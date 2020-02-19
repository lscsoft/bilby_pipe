"""
argument parser for bilby_pipe, adapted from configargparse.ArgParser.
"""

import os
import re
import sys

import configargparse

from .utils import get_version_information, logger


class HyphenStr(str):
    def __new__(cls, content):
        return super(HyphenStr, cls).__new__(cls, content.replace("_", "-"))


class BilbyArgParser(configargparse.ArgParser):
    """
    The main entry point for command-line parsing
    """

    numbers = dict()
    comments = dict()
    inline_comments = dict()

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
            config_file_parser = BilbyConfigFileParser()
            ini_stream = config_stream.pop()  # get ini file's steam
            ini_items, numbers, comments, inline_comments = config_file_parser.parse(
                ini_stream
            )
            ini_stream.close()
            self.numbers = numbers
            self.comments = comments
            self.inline_comments = inline_comments
            corrected_items = dict(
                (key.replace("_", "-"), val) for key, val in ini_items.items()
            )
            file_contents = config_file_parser.serialize(corrected_items)

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
                key = HyphenStr(key)
                normalized_args.append(key)
                normalized_args.append(value)
            else:
                if arg.startswith("--"):
                    arg.replace("_", "-")
                normalized_args.append(arg)

        return normalized_args

    def write_to_file(
        self,
        filename,
        args=None,
        overwrite=False,
        include_description=False,
        exclude_default=False,
        comment=None,
    ):
        if os.path.isfile(filename) and not overwrite:
            logger.warning(
                "File {} already exists, not writing to file.".format(filename)
            )
        with open(filename, "w") as ff:
            __version__ = get_version_information()
            if include_description:
                print(
                    "## This file was written with bilby_pipe version {}\n".format(
                        __version__
                    ),
                    file=ff,
                )
            if isinstance(comment, str):
                print("#" + comment + "\n", file=ff)
            for group in self._action_groups[2:]:
                print("#" * 80, file=ff)
                print("## {}".format(group.title), file=ff)
                if include_description:
                    print("# {}".format(group.description), file=ff)
                print("#" * 80 + "\n", file=ff)
                for action in group._group_actions:
                    if include_description:
                        print("# {}".format(action.help), file=ff)
                    dest = action.dest
                    hyphen_dest = HyphenStr(dest)
                    if isinstance(args, dict):
                        if action.dest in args:
                            value = args[dest]
                        elif hyphen_dest in args:
                            value = args[hyphen_dest]
                        else:
                            value = action.default
                    else:
                        value = getattr(args, dest, action.default)

                    if exclude_default and value == action.default:
                        continue
                    self.write_comment_if_needed(hyphen_dest, ff)
                    self.write_line(hyphen_dest, value, ff)
                print("", file=ff)

    def write_comment_if_needed(self, hyphen_dest, ff):
        """ Determine if the line is associated with a comment """
        if hyphen_dest in self.numbers:
            previous_line = self.numbers[hyphen_dest] - 1
            if previous_line in self.comments:
                print(self.comments[previous_line], file=ff)

    def write_line(self, hyphen_dest, value, ff):
        if hyphen_dest in self.numbers:
            comment = self.inline_comments.get(self.numbers[hyphen_dest], "")
        else:
            comment = ""
        print("{}={}{}".format(hyphen_dest, value, comment), file=ff)


class BilbyConfigFileParser(configargparse.DefaultConfigFileParser):
    def parse(self, stream):
        """Parses the keys + values from a config file."""

        items = dict()
        numbers = dict()
        comments = dict()
        inline_comments = dict()
        for ii, line in enumerate(stream):
            line = line.strip()
            if not line:
                continue
            if line[0] in ["#", ";", "["] or line.startswith("---"):
                comments[ii] = line
                continue
            if len(line.split("#")) > 1:
                inline_comments[ii] = "  #" + "#".join(line.split("#")[1:])
                line = line.split("#")[0]
            white_space = "\\s*"
            key = r"(?P<key>[^:=;#\s]+?)"
            value = white_space + r"[:=\s]" + white_space + "(?P<value>.+?)"
            comment = white_space + "(?P<comment>\\s[;#].*)?"

            key_only_match = re.match("^" + key + comment + "$", line)
            if key_only_match:
                key = HyphenStr(key_only_match.group("key"))
                items[key] = "true"
                numbers[key] = ii
                continue

            key_value_match = re.match("^" + key + value + comment + "$", line)
            if key_value_match:
                key = HyphenStr(key_value_match.group("key"))
                value = key_value_match.group("value")

                if value.startswith("[") and value.endswith("]"):
                    # handle special case of lists
                    value = [elem.strip() for elem in value[1:-1].split(",")]

                items[key] = value
                numbers[key] = ii
                continue

            raise configargparse.ConfigFileParserException(
                "Unexpected line {} in {}: {}".format(
                    ii, getattr(stream, "name", "stream"), line
                )
            )

        items = self.reconstruct_multiline_dictionary(items)
        return items, numbers, comments, inline_comments

    def reconstruct_multiline_dictionary(self, items):
        keys = list(items.keys())
        vals = list(items.values())
        for ii, val in enumerate(vals):
            if "{" in val and "}" not in val:
                sub_ii = 1
                sub_dict_vals = []
                if val != "{":
                    sub_dict_vals.append(val.rstrip("{"))
                while True:
                    next_line = "{}: {}".format(keys[ii + sub_ii], vals[ii + sub_ii])
                    items.pop(keys[ii + sub_ii])
                    if "}" not in next_line:
                        if "{" in next_line:
                            raise ValueError("Unable to pass multi-line config file")
                        sub_dict_vals.append(next_line)
                        sub_ii += 1
                        continue
                    elif next_line == "}: true":
                        sub_dict_vals.append("}")
                        break
                    else:
                        sub_dict_vals.append(next_line)
                        break
                sub_dict_vals_with_comma = [
                    vv.rstrip(",").lstrip(",") for vv in sub_dict_vals
                ]
                items[keys[ii]] = "{" + (", ".join(sub_dict_vals_with_comma)).lstrip(
                    "{"
                )
        return items
