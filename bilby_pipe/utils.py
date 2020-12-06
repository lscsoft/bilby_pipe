"""
A set of generic utilities used in bilby_pipe
"""
import ast
import json
import logging
import math
import os
import pickle
import re
import subprocess
import sys
import urllib
import urllib.request
from importlib import import_module
from pathlib import Path

import bilby

CHECKPOINT_EXIT_CODE = 77


class tcolors:
    WARNING = "\u001b[31m"
    KEY = "\033[93m"
    VALUE = "\033[91m"
    HIGHLIGHT = "\033[95m"
    END = "\033[0m"


def get_colored_string(msg_list, color="WARNING"):
    if isinstance(msg_list, str):
        msg_list = [msg_list]
    colstr = getattr(tcolors, color)
    msg = [colstr] + msg_list + [tcolors.END]
    return " ".join(msg)


class BilbyPipeError(Exception):
    def __init__(self, message):
        super().__init__(message)


class BilbyPipeInternalError(Exception):
    def __init__(self, message):
        super().__init__(message)


class ArgumentsString(object):
    """ A convenience object to aid in the creation of argument strings """

    def __init__(self):
        self.argument_list = []

    def append(self, argument):
        self.argument_list.append(argument)

    def add_positional_argument(self, value):
        self.argument_list.append(f"{value}")

    def add_flag(self, flag):
        self.argument_list.append(f"--{flag}")

    def add(self, argument, value):
        self.argument_list.append(f"--{argument}")
        self.argument_list.append(f"{value}")

    def add_unknown_args(self, unknown_args):
        self.argument_list += unknown_args

    def add_command_line_arguments(self):
        """ Adds command line arguments given in addition to the ini file """
        command_line_args_list = get_command_line_arguments()
        # Remove the first positional ini-file argument
        command_line_args_list = command_line_args_list[1:]
        self.argument_list += command_line_args_list

    def print(self):
        return " ".join(self.argument_list)


class DataDump(object):
    def __init__(
        self,
        label,
        outdir,
        trigger_time,
        likelihood_lookup_table,
        likelihood_roq_weights,
        likelihood_roq_params,
        priors_dict,
        priors_class,
        interferometers,
        meta_data,
        idx,
    ):
        self.trigger_time = trigger_time
        self.label = label
        self.outdir = outdir
        self.interferometers = interferometers
        self.likelihood_lookup_table = likelihood_lookup_table
        self.likelihood_roq_weights = likelihood_roq_weights
        self.likelihood_roq_params = likelihood_roq_params
        self.priors_dict = priors_dict
        self.priors_class = priors_class
        self.meta_data = meta_data
        self.idx = idx

    @staticmethod
    def get_filename(outdir, label):
        return os.path.join(outdir, "_".join([label, "data_dump.pickle"]))

    @property
    def filename(self):
        return self.get_filename(self.outdir, self.label)

    def to_pickle(self):
        with open(self.filename, "wb+") as file:
            pickle.dump(self, file)

    @classmethod
    def from_pickle(cls, filename=None):
        """Loads in a data dump

        Parameters
        ----------
        filename: str
            If given, try to load from this filename

        """
        with open(filename, "rb") as file:
            res = pickle.load(file)
        if res.__class__ != cls:
            raise TypeError("The loaded object is not a DataDump")
        return res


class NoneWrapper(object):
    """
    Wrapper around other types so that "None" always evaluates to None.

    This is needed to properly read None from ini files.

    Example
    -------
    >>> nonestr = NoneWrapper(str)
    >>> nonestr("None")
    None
    >>> nonestr(None)
    None
    >>> nonestr("foo")
    "foo"

    >>> noneint = NoneWrapper(int)
    >>> noneint("None")
    None
    >>> noneint(None)
    None
    >>> noneint(0)
    0
    """

    def __init__(self, type):
        self.type = type

    def __call__(self, val):
        if val == "None" or val is None:
            return None
        else:
            return self.type(val)


nonestr = NoneWrapper(str)
noneint = NoneWrapper(int)
nonefloat = NoneWrapper(float)

DEFAULT_DISTANCE_LOOKUPS = {
    "high_mass": (1e2, 5e3),
    "4s": (1e2, 5e3),
    "8s": (1e2, 5e3),
    "16s": (1e2, 4e3),
    "32s": (1e2, 3e3),
    "64s": (50, 2e3),
    "128s": (1, 5e2),
    "128s_tidal": (1, 5e2),
    "128s_tidal_lowspin": (1, 5e2),
}

DURATION_LOOKUPS = {
    "high_mass": 4,
    "4s": 4,
    "8s": 8,
    "16s": 16,
    "32s": 32,
    "64s": 64,
    "128s": 128,
    "128s_tidal": 128,
    "128s_tidal_lowspin": 128,
}

MAXIMUM_FREQUENCY_LOOKUPS = {
    "high_mass": 1024,
    "4s": 1024,
    "8s": 2048,
    "16s": 2048,
    "32s": 2048,
    "64s": 2048,
    "128s": 4096,
    "128s_tidal": 2048,
    "128s_tidal_lowspin": 2048,
}

SAMPLER_SETTINGS = {
    "Default": {
        "nlive": 1000,
        "walks": 50,
        "check_point_plot": True,
        "n_check_point": 10000,
    },
    "FastTest": {
        "nlive": 500,
        "walks": 50,
        "dlogz": 2,
        "check_point_plot": True,
        "n_check_point": 1000,
    },
}


def get_command_line_arguments():
    """ Helper function to return the list of command line arguments """
    return sys.argv[1:]


def run_command_line(arguments, directory=None):
    if directory:
        pwd = os.path.abspath(".")
        os.chdir(directory)
    else:
        pwd = None
    print(f"\nRunning command $ {' '.join(arguments)}\n")
    subprocess.call(arguments)
    if pwd:
        os.chdir(pwd)


def parse_args(input_args, parser, allow_unknown=True):
    """Parse an argument list using parser generated by create_parser()

    Parameters
    ----------
    input_args: list
        A list of arguments

    Returns
    -------
    args: argparse.Namespace
        A simple object storing the input arguments
    unknown_args: list
        A list of any arguments in `input_args` unknown by the parser

    """

    if len(input_args) == 0:
        raise BilbyPipeError("No command line arguments provided")

    ini_file = input_args[0]
    if os.path.isfile(ini_file) is False:
        if os.path.isfile(os.path.basename(ini_file)):
            input_args[0] = os.path.basename(ini_file)

    args, unknown_args = parser.parse_known_args(input_args)
    return args, unknown_args


def check_directory_exists_and_if_not_mkdir(directory):
    """Checks if the given directory exists and creates it if it does not exist

    Parameters
    ----------
    directory: str
        Name of the directory

    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.debug(f"Making directory {directory}")
    else:
        logger.debug(f"Directory {directory} exists")


def setup_logger(outdir=None, label=None, log_level="INFO"):
    """Setup logging output: call at the start of the script to use

    Parameters
    ----------
    outdir, label: str
        If supplied, write the logging output to outdir/label.log
    log_level: str, optional
        ['debug', 'info', 'warning']
        Either a string from the list above, or an integer as specified
        in https://docs.python.org/2/library/logging.html#logging-levels
    """

    if "-v" in sys.argv or "--verbose" in sys.argv:
        log_level = "DEBUG"

    if isinstance(log_level, str):
        try:
            level = getattr(logging, log_level.upper())
        except AttributeError:
            raise ValueError(f"log_level {log_level} not understood")
    else:
        level = int(log_level)

    logger = logging.getLogger("bilby_pipe")
    logger.propagate = False
    logger.setLevel(level)

    streams = [isinstance(h, logging.StreamHandler) for h in logger.handlers]
    if len(streams) == 0 or not all(streams):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(name)s %(levelname)-8s: %(message)s", datefmt="%H:%M"
            )
        )
        stream_handler.setLevel(level)
        logger.addHandler(stream_handler)

    if any([isinstance(h, logging.FileHandler) for h in logger.handlers]) is False:
        if label:
            if outdir:
                check_directory_exists_and_if_not_mkdir(outdir)
            else:
                outdir = "."
            log_file = f"{outdir}/{label}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)-8s: %(message)s", datefmt="%H:%M"
                )
            )

            file_handler.setLevel(level)
            logger.addHandler(file_handler)

    for handler in logger.handlers:
        handler.setLevel(level)


def get_outdir_name(outdir, fail_on_match=False, base_increment="A"):
    # Check if the directory exists
    if os.path.exists(outdir) is False:
        return outdir
    else:
        msg = f"The outdir {outdir} already exists."
        if fail_on_match:
            raise BilbyPipeError(msg)

        while os.path.exists(outdir):
            # Test if outdir is already an incremented-name
            if outdir[-2] == "_" and outdir[-1].isalnum():
                outdir = outdir[:-1] + chr(ord(outdir[-1]) + 1)
            else:
                outdir += f"_{base_increment}"

        msg += f" Incrementing outdir to {outdir}"
        logger.warning(get_colored_string(msg))
        return outdir


def log_version_information():
    import bilby

    version = get_version_information()
    logger.info(f"Running bilby_pipe version: {version}")
    logger.info(f"Running bilby: {bilby.__version__}")


def get_version_information():
    version_file = Path(__file__).parent / ".version"
    try:
        with open(version_file, "r") as f:
            return f.readline().rstrip()
    except FileNotFoundError:
        print("No version information file '.version' found")
        return ""


def convert_string_to_tuple(string, key=None, n=None):
    """Convert a string to a tuple

    Parameters
    ----------
    string: str
        The string to convert
    key: str
        Name used for printing useful debug messages
    n: int
        The length of the string to check against, if None no check performed.

    Returns
    -------
    tup: tuple
        A tuple
    """
    try:
        tup = ast.literal_eval(string)
    except ValueError as e:
        if key is not None:
            raise BilbyPipeError(f"Error {e}: unable to convert {key}: {string}")
        else:
            raise BilbyPipeError(f"Error {e}: unable to {string}")
    if n is not None:
        if len(tup) != n:
            raise BilbyPipeError(
                f"Passed string {string} should be a tuple of length {n}"
            )

    return tup


def convert_string_to_dict(string, key=None):
    """Convert a string repr of a string to a python dictionary

    Parameters
    ----------
    string: str
        The string to convert
    key: str (None)
        A key, used for debugging
    """
    if string == "None":
        return None
    string = strip_quotes(string)
    # Convert equals to colons
    string = string.replace("=", ":")
    string = string.replace(" ", "")

    string = re.sub(r'([A-Za-z/\.0-9\-\+][^\[\],:"}]*)', r'"\g<1>"', string)

    # Force double quotes around everything
    string = string.replace('""', '"')

    # Evaluate as a dictionary of str: str
    try:
        dic = ast.literal_eval(string)
        if isinstance(dic, str):
            raise BilbyPipeError(f"Unable to format {string} into a dictionary")
    except (ValueError, SyntaxError) as e:
        if key is not None:
            raise BilbyPipeError(f"Error {e}. Unable to parse {key}: {string}")
        else:
            raise BilbyPipeError(f"Error {e}. Unable to parse {string}")

    # Convert values to bool/floats/ints where possible
    dic = convert_dict_values_if_possible(dic)

    return dic


def convert_string_to_list(string):
    """Converts a string to a list, e.g. the mode_array waveform argument

    See tests/utils_test for tested behaviour.

    Parameters:
    -----------
    string: str
        The input string to convert

    Returns
    -------
    new_list: list
        A list (or lists)

    """

    if type(string) not in [str, list]:
        return string

    if (string.count("[") == 1) and (string.count("]") == 1):
        string = str(sanitize_string_for_list(string))

    try:
        new_list = ast.literal_eval(str(string))
    except ValueError:
        return string

    if not isinstance(new_list, list):
        return new_list

    for ii, ell in enumerate(new_list):
        new_list[ii] = convert_string_to_list(ell)

    return new_list


def sanitize_string_for_list(string):
    string = string.replace(",", " ")
    string = string.replace("[", "")
    string = string.replace("]", "")
    string = string.replace('"', "")
    string = string.replace("'", "")
    string_list = string.split()
    return string_list


def convert_dict_values_if_possible(dic):
    for key in dic:
        if isinstance(dic[key], str) and dic[key].lower() == "true":
            dic[key] = True
        elif isinstance(dic[key], str) and dic[key].lower() == "false":
            dic[key] = False
        elif isinstance(dic[key], str):
            dic[key] = string_to_int_float(dic[key])
        elif isinstance(dic[key], dict):
            dic[key] = convert_dict_values_if_possible(dic[key])
    return dic


def write_config_file(config_dict, filename, comment=None, remove_none=False):
    """Writes ini file

    Parameters
    ----------
    config_dict: dict
        Dictionary of parameters for ini file
    filename: str
        Filename to write the config file to
    comment: str
        Additional information on ini file generation
    remove_none: bool
        If true, remove None's from the config_dict before writing otherwise
        a ValueError is raised
    """
    logger.warning(
        "write_config_file has been deprecated, it will be removed in a future version"
    )

    if remove_none:
        config_dict = {key: val for key, val in config_dict.items() if val is not None}
    if None in config_dict.values():
        raise ValueError("config-dict is not complete")
    with open(filename, "w+") as file:
        if comment is not None:
            print(f"{comment}", file=file)
        for key, val in config_dict.items():
            print(f"{key}={val}", file=file)


def test_connection():
    """ A generic test to see if the network is reachable """
    try:
        urllib.request.urlopen("https://google.com", timeout=1.0)
    except urllib.error.URLError:
        raise BilbyPipeError(
            "It appears you are not connected to a network and so won't be "
            "able to interface with GraceDB. You may wish to specify the "
            " local-generation argument either in the configuration file "
            "or by passing the --local-generation command line argument"
        )


def strip_quotes(string):
    try:
        return string.replace('"', "").replace("'", "")
    except AttributeError:
        return string


def string_to_int_float(s):
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def is_a_power_of_2(num):
    num = int(num)
    return num != 0 and ((num & (num - 1)) == 0)


def next_power_of_2(x):
    return 1 if x == 0 else 2 ** math.ceil(math.log2(x))


def request_memory_generation_lookup(duration, roq=False):
    """ Function to determine memory required at the data generation step """
    if roq:
        return int(max([8, min([60, duration])]))
    else:
        return 8


def get_time_prior(time, uncertainty, name="geocent_time", latex_label="$t_c$"):
    """Generate a time prior given some uncertainty.

    Parameters
    ----------
    time: float
        The GPS geocent_time (time of coalescence at the center of the Earth)
    uncertainty: float
        The +/- uncertainty based around the geocenter time.
    name: str
        The name of the time parameter
    latex_label: str
        The latex label for the time parameter

    Returns
    -------
    A bilby.core.prior.Uniform for the time parameter.

    """
    return bilby.core.prior.Uniform(
        minimum=time - uncertainty,
        maximum=time + uncertainty,
        name=name,
        latex_label=latex_label,
        unit="$s$",
    )


def get_geocent_time_with_uncertainty(geocent_time, uncertainty):
    """Get a new geocent time within some uncertainty from the original geocent time.

    Parameters
    ----------
    geocent_time: float
        The GPS geocent_time (time of coalescence at the center of the Earth)
    uncertainty: float
        The +/- uncertainty based around the geocenter time.

    Returns
    -------
    A geocent GPS time (float) inside the range of geocent time - uncertainty and
    geocent time + uncertainty.

    """
    geocent_time_prior = get_time_prior(geocent_time, uncertainty)
    return geocent_time_prior.sample()


def convert_detectors_input(string):
    """Convert string inputs into a standard form for the detectors

    Parameters
    ----------
    string: str
        A string representation to be converted

    Returns
    -------
    detectors: list
        A sorted list of detectors

    """
    if string is None:
        raise BilbyPipeError("No detector input")
    if isinstance(string, list):
        string = ",".join(string)
    if isinstance(string, str) is False:
        raise BilbyPipeError(f"Detector input {string} not understood")
    # Remove square brackets
    string = string.replace("[", "").replace("]", "")
    # Remove added quotes
    string = strip_quotes(string)
    # Replace multiple spaces with a single space
    string = " ".join(string.split())
    # Spaces can be either space or comma in input, convert to comma
    string = string.replace(" ,", ",").replace(", ", ",").replace(" ", ",")

    detectors = string.split(",")

    detectors.sort()
    detectors = [det.upper() for det in detectors]
    return detectors


def convert_prior_string_input(string):
    string = string.replace(" ", "")
    string = string.replace(":", "=")
    prior_dict_of_strings = {}
    for part in comma_partition(string):
        if len(part) > 0:
            prior_dict_of_strings.update(kv_parser(part))
    return prior_dict_of_strings


def comma_partition(s):
    """Partitions `s` at top-level commas"""
    s = s.strip("{").strip("}")
    in_parens = 0
    ixs = []
    for i, c in enumerate(s):
        if c == "(":
            in_parens += 1
        if c == ")":
            in_parens -= 1
        if not in_parens and c == ",":
            ixs.append(i)
    return [s[sc] for sc in make_partition_slices(ixs)]


def make_partition_slices(ixs):
    """Yields partitioning slices, skipping each index of `ixs`"""
    ix_x = [None] + ixs
    ix_y = ixs + [None]
    for x, y in zip(ix_x, ix_y):
        yield slice(x + 1 if x else x, y)


def kv_parser(kv_str, remove_leading_namespace=False):
    """Takes a string in 'K=V' format and returns dictionary."""
    try:
        k, v = kv_str.split("=", 1)
        return {k: v}
    except ValueError:
        raise BilbyPipeInternalError(f"Error in ini-dict reader when reading {kv_str}")


def check_if_represents_int(s):
    """Checks if the string/bytes-like object/number s represents an int"""
    try:
        int(s)
        return True
    except ValueError:
        return False


def pretty_print_dictionary(dictionary):
    """Convert an input dictionary to a pretty-printed string

    Parameters
    ----------
    dictionary: dict
        Input dictionary

    Returns
    -------
    pp: str
        The dictionary pretty-printed as a string

    """
    dict_as_str = {key: str(val) for key, val in dictionary.items()}
    return json.dumps(dict_as_str, indent=2)


class DuplicateErrorDict(dict):
    """An dictionary with immutable key-value pairs

    Once a key-value pair is initialized, any attempt to update the value for
    an existing key will raise a BilbyPipeError.

    Raises
    ------
    BilbyPipeError:
        When a user attempts to update an existing key.

    """

    def __init__(self, color=True, *args):
        dict.__init__(self, args)
        self.color = color

    def __setitem__(self, key, val):
        if key in self:
            msg = f"Your ini file contains duplicate '{key}' keys"
            if self.color:
                msg = get_colored_string(msg)
            raise BilbyPipeError(msg)
        dict.__setitem__(self, key, val)


def get_function_from_string_path(python_path):
    split = python_path.split(".")
    module_str = ".".join(split[:-1])
    func_str = split[-1]
    try:
        return getattr(import_module(module_str), func_str)
    except ImportError as e:
        raise BilbyPipeError(
            f"Failed to load function {python_path}, full message: {e}"
        )


setup_logger()
logger = logging.getLogger("bilby_pipe")
