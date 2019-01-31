#!/usr/bin/env python
"""
argument parser for bilby_pipe, adapted from configargparse.ArgParser.
"""

import io
import os
import re
import sys
import argparse
import configargparse

from collections import OrderedDict


class BilbyArgParser(configargparse.ArgParser):
    def parse_known_args(
        self, args=None, namespace=None, config_file_contents=None, env_vars=os.environ
    ):
        """Supports all the same args as the ArgumentParser.parse_args(..),
        as well as the following additional args.

        Additional Args:
            args: a list of args as in argparse, or a string (eg. "-x -y bla")
            config_file_contents: String. Used for testing.
            env_vars: Dictionary. Used for testing.
        """

        # used while parsing args to keep track of where they came from
        _COMMAND_LINE_SOURCE_KEY = "command_line"
        _ENV_VAR_SOURCE_KEY = "environment_variables"
        _CONFIG_FILE_SOURCE_KEY = "config_file"
        _DEFAULTS_SOURCE_KEY = "defaults"

        ACTION_TYPES_THAT_DONT_NEED_A_VALUE = (
            argparse._StoreTrueAction,
            argparse._StoreFalseAction,
            argparse._CountAction,
            argparse._StoreConstAction,
            argparse._AppendConstAction,
        )

        if args is None:
            args = sys.argv[1:]
        elif isinstance(args, str):
            args = args.split()
        else:
            args = list(args)

        # normalize args by converting args like --key=value to --key value
        normalized_args = list()
        for arg in args:
            if arg and arg[0] in self.prefix_chars and "=" in arg:
                key, value = arg.split("=", 1)
                key = key.replace("_", "-")
                normalized_args.append(key)
                normalized_args.append(value)
            else:
                if arg.startswith("--"):
                    arg.replace("_", "-")
                normalized_args.append(arg)
        args = normalized_args

        for a in self._actions:
            a.is_positional_arg = not a.option_strings

        # maps a string describing the source (eg. env var) to a settings dict
        # to keep track of where values came from (used by print_values()).
        # The settings dicts for env vars and config files will then map
        # the config key to an (argparse Action obj, string value) 2-tuple.
        self._source_to_settings = OrderedDict()
        if args:
            a_v_pair = (None, list(args))  # copy args list to isolate changes
            self._source_to_settings[_COMMAND_LINE_SOURCE_KEY] = {"": a_v_pair}

        # handle auto_env_var_prefix __init__ arg by setting a.env_var as needed
        if self._auto_env_var_prefix is not None:
            for a in self._actions:
                config_file_keys = self.get_possible_config_keys(a)
                if config_file_keys:
                    if not (a.env_var or a.is_positional_arg):
                        if not (a.is_config_file_arg):
                            if not (a.is_write_out_config_file_arg):
                                if not (isinstance(a, argparse._HelpAction)):
                                    stripped_config_file_key = config_file_keys[
                                        0
                                    ].strip(self.prefix_chars)
                                    a.env_var = (
                                        self._auto_env_var_prefix
                                        + stripped_config_file_key
                                    )
                                    a.env_var = a.env_var.replace("-", "_").upper()

        # add env var settings to the commandline that aren't there already
        env_var_args = []
        actions_with_env_var_values = []
        for a in self._actions:
            if not a.is_positional_arg:
                if a.env_var:
                    if a.env_var in env_vars:
                        if not configargparse.already_on_command_line(
                            args, a.option_strings
                        ):
                            actions_with_env_var_values.append(a)

        for action in actions_with_env_var_values:
            key = action.env_var
            value = env_vars[key]
            # Make list-string into list.
            if action.nargs or isinstance(action, argparse._AppendAction):
                element_capture = re.match("\[(.*)\]", value)  # noqa
                if element_capture:
                    value = [
                        val.strip()
                        for val in element_capture.group(1).split(",")
                        if val.strip()
                    ]
            env_var_args += self.convert_item_to_command_line_arg(action, key, value)

        args = args + env_var_args

        if env_var_args:
            self._source_to_settings[_ENV_VAR_SOURCE_KEY] = OrderedDict(
                [
                    (a.env_var, (a, env_vars[a.env_var]))
                    for a in actions_with_env_var_values
                ]
            )

        # before parsing any config files, check if -h was specified.
        supports_help_arg = any(
            a for a in self._actions if isinstance(a, argparse._HelpAction)
        )
        skip_config_file_parsing = supports_help_arg and (
            "-h" in args or "--help" in args
        )

        # prepare for reading config file(s)
        known_config_keys = dict(
            (config_key, action)
            for action in self._actions
            for config_key in self.get_possible_config_keys(action)
        )

        # open the config file(s)
        config_streams = []
        if config_file_contents is not None:
            stream = io.StringIO(config_file_contents)
            stream.name = "method arg"
            config_streams = [stream]
        elif not skip_config_file_parsing:
            config_streams = self._open_config_files(args)

        # parse each config file
        for stream in reversed(config_streams):
            try:
                config_items = self._config_file_parser.parse(stream)
            except configargparse.ConfigFileParserException as e:
                self.error(e)
            finally:
                if hasattr(stream, "close"):
                    stream.close()

            # add each config item to the commandline unless it's there already
            config_args = []
            for key, value in config_items.items():
                key = key.replace("_", "-")
                if key in known_config_keys:
                    action = known_config_keys[key]
                    discard_this_key = configargparse.already_on_command_line(
                        args, action.option_strings
                    )
                else:
                    action = None
                    discard_this_key = (
                        self._ignore_unknown_config_file_keys
                        or configargparse.already_on_command_line(
                            args,
                            [
                                self.get_command_line_key_for_unknown_config_file_setting(
                                    key
                                )
                            ],
                        )
                    )

                if not discard_this_key:
                    config_args += self.convert_item_to_command_line_arg(
                        action, key, value
                    )
                    source_key = "%s|%s" % (_CONFIG_FILE_SOURCE_KEY, stream.name)
                    if source_key not in self._source_to_settings:
                        self._source_to_settings[source_key] = OrderedDict()
                    self._source_to_settings[source_key][key] = (action, value)

            args = args + config_args

        # save default settings for use by print_values()
        default_settings = OrderedDict()
        for action in self._actions:
            cares_about_default_value = (
                not action.is_positional_arg
                or action.nargs in [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
            )
            if (
                configargparse.already_on_command_line(args, action.option_strings)
                or not cares_about_default_value
                or action.default is None
                or action.default == argparse.SUPPRESS
                or isinstance(action, ACTION_TYPES_THAT_DONT_NEED_A_VALUE)
            ):
                continue
            else:
                if action.option_strings:
                    key = action.option_strings[-1]
                else:
                    key = action.dest
                default_settings[key] = (action, str(action.default))

        if default_settings:
            self._source_to_settings[_DEFAULTS_SOURCE_KEY] = default_settings

        # parse all args (including commandline, config file, and env var)
        namespace, unknown_args = argparse.ArgumentParser.parse_known_args(
            self, args=args, namespace=namespace
        )
        # handle any args that have is_write_out_config_file_arg set to true
        # check if the user specified this arg on the commandline
        output_file_paths = [
            getattr(namespace, a.dest, None)
            for a in self._actions
            if getattr(a, "is_write_out_config_file_arg", False)
        ]
        output_file_paths = [a for a in output_file_paths if a is not None]
        self.write_config_file(namespace, output_file_paths, exit_after=True)
        return namespace, unknown_args
