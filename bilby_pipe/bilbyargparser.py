"""
argument parser for bilby_pipe, adapted from configargparse.ArgParser.
"""

import os
import sys
import configargparse


class BilbyArgParser(configargparse.ArgParser):
    """
    The main entry point for command-line parsing
    """

    def parse_known_args(
        self, args=None, namespace=None, config_file_contents=None, env_vars=os.environ
    ):
        """Supports all the same args as the ArgumentParser.parse_args(..),
        as well as the following additional args.

        Parameters
        ----------
        args: None, str, List[str]
             List of strings to parse. The default is taken from sys.argv
             Can also be a string "-x -y bla"

        namespace: argparse.Namespace
            The Namespace object that will be returned by parse_args().

        config_file_contents: None
            Present because inherited from abstract method. The config_file_contents
            are read from the config_file passed in the args.

        env_vars: dict
            Dictionary of environment variables

        Returns
        -------
        namespace: argparse.Namespace
            An object to take the attributes parsed.

        unknown_args: List[str]
            List of the args unrecognised by the parser

        """
        namespace, unknown_args = super(BilbyArgParser, self).parse_known_args(
            args=self._preprocess_args(args),
            namespace=namespace,
            config_file_contents=self._preprocess_config_file_contents(args),
            env_vars=env_vars,
        )
        return namespace, unknown_args

    def _preprocess_config_file_contents(self, args):
        """Reads config file into string and formats it for ArgParser

        Parameters
        ----------
        args: None, list, str
            The input args to be parsed. Creates config_file_content
            only if one of the args is a config_file

        Returns
        -------
        file_contents: str
            The content of the config files, correctly formatted

        file_contents: None
            If no config file specified
        """
        file_contents = None
        config_stream = self._open_config_files(args)
        if config_stream:
            ini_stream = config_stream.pop()  # get ini file's steam
            ini_items = self._config_file_parser.parse(ini_stream)
            corrected_items = dict(
                (key.replace("_", "-"), val) for key, val in ini_items.items()
            )
            file_contents = self._config_file_parser.serialize(corrected_items)
        return file_contents

    def _preprocess_args(self, args):
        """Processes args into correct format for ArgParser

        Parameters
        ----------
        args: None, list, str
            The input args to be parsed.

        Returns
        -------
        normalized_args: List[string]
            args list normalised to "--key value"

        """
        # format args into list
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

        return normalized_args
