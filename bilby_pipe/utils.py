"""
A set of generic utilities used in bilby_pipe
"""
import ast
import logging
import math
import os
import pickle
import re
import subprocess
import sys
import urllib
import urllib.request
from pathlib import Path

import bilby


class tcolors:
    WARNING = "\u001b[31m"
    KEY = "\033[93m"
    VALUE = "\033[91m"
    HIGHLIGHT = "\033[95m"
    END = "\033[0m"


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
        self.argument_list.append("{}".format(value))

    def add_flag(self, flag):
        self.argument_list.append("--{}".format(flag))

    def add(self, argument, value):
        self.argument_list.append("--{}".format(argument))
        self.argument_list.append("{}".format(value))

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
        """ Loads in a data dump

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
    print("\nRunning command $ {}\n".format(" ".join(arguments)))
    subprocess.call(arguments)
    if pwd:
        os.chdir(pwd)


def parse_args(input_args, parser, allow_unknown=True):
    """ Parse an argument list using parser generated by create_parser()

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
    """ Checks if the given directory exists and creates it if it does not exist

    Parameters
    ----------
    directory: str
        Name of the directory

    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.debug("Making directory {}".format(directory))
    else:
        logger.debug("Directory {} exists".format(directory))


def setup_logger(outdir=None, label=None, log_level="INFO"):
    """ Setup logging output: call at the start of the script to use

    Parameters
    ----------
    outdir, label: str
        If supplied, write the logging output to outdir/label.log
    log_level: str, optional
        ['debug', 'info', 'warning']
        Either a string from the list above, or an integer as specified
        in https://docs.python.org/2/library/logging.html#logging-levels
    """

    if "-v" in sys.argv:
        log_level = "DEBUG"

    if isinstance(log_level, str):
        try:
            level = getattr(logging, log_level.upper())
        except AttributeError:
            raise ValueError("log_level {} not understood".format(log_level))
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
            log_file = "{}/{}.log".format(outdir, label)
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


def log_version_information():
    import bilby

    version = get_version_information()
    logger.info("Running bilby_pipe version: {}".format(version))
    logger.info("Running bilby: {}".format(bilby.__version__))


def get_version_information():
    version_file = Path(__file__).parent / ".version"
    try:
        with open(version_file, "r") as f:
            return f.readline().rstrip()
    except FileNotFoundError:
        print("No version information file '.version' found")
        return ""


def convert_string_to_tuple(string, key=None, n=None):
    """" Convert a string to a tuple

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
            raise BilbyPipeError(
                "Error {}: unable to convert {}: {}".format(e, key, string)
            )
        else:
            raise BilbyPipeError("Error {}: unable to {}".format(e, string))
    if n is not None:
        if len(tup) != n:
            raise BilbyPipeError(
                "Passed string {} should be a tuple of length {}".format(string, n)
            )

    return tup


def convert_string_to_dict(string, key=None):
    """ Convert a string repr of a string to a python dictionary

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
            raise BilbyPipeError("Unable to format {} into a dictionary".format(string))
    except (ValueError, SyntaxError) as e:
        if key is not None:
            raise BilbyPipeError(
                "Error {}. Unable to parse {}: {}".format(e, key, string)
            )
        else:
            raise BilbyPipeError("Error {}. Unable to parse {}".format(e, string))

    # Convert values to bool/floats/ints where possible
    dic = convert_dict_values_if_possible(dic)

    return dic


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
    """ Writes ini file

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
            print("{}".format(comment), file=file)
        for key, val in config_dict.items():
            print("{}={}".format(key, val), file=file)


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


def get_geocent_prior(geocent_time, uncertainty):
    """"Generate a geocent time prior given some uncertainty.

    Parameters
    ----------
    geocent_time: float
        The GPS geocent_time (time of coalescence at the center of the Earth)
    uncertainty: float
        The +/- uncertainty based around the geocenter time.

    Returns
    -------
    A bilby.core.prior.Uniform for the geocent_time.

    """
    return bilby.core.prior.Uniform(
        minimum=geocent_time - uncertainty,
        maximum=geocent_time + uncertainty,
        name="geocent_time",
        latex_label="$t_c$",
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
    geocent_time_prior = get_geocent_prior(geocent_time, uncertainty)
    return geocent_time_prior.sample()


def convert_detectors_input(string):
    """ Convert string inputs into a standard form for the detectors

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
        raise BilbyPipeError("Detector input {} not understood".format(string))
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
    """Takes a string in 'K=V' format and returns dictionary.
    """
    try:
        k, v = kv_str.split("=", 1)
        return {k: v}
    except ValueError:
        raise BilbyPipeInternalError(
            "Error in ini-dict reader when reading {}".format(kv_str)
        )


setup_logger()
logger = logging.getLogger("bilby_pipe")
