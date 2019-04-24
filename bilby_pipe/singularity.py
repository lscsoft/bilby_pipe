""" Script to run a script in a singularity container """
import sys
import subprocess

from bilby_pipe.bilbyargparser import BilbyArgParser
from bilby_pipe.main import parse_args
from bilby_pipe.utils import logger


def create_parser():
    """ Generate a parser for the singularity script

    Additional options can be added to the returned parser beforing calling
    `parser.parse_args` to generate the arguments`

    Returns
    -------
    parser: BilbyArgParser
        A parser with all the default options already added

    """
    parser = BilbyArgParser(ignore_unknown_config_file_keys=True)
    parser.add("-s", "--simg", type=str, help="The singularity image", required=True)
    parser.add("--bilby-pipe-executable", type=str, required=True)
    return parser


def main():
    args, unknown_args = parse_args(sys.argv[1:], create_parser())
    exec_args = ["singularity", "exec", args.simg]
    exec_args.append("bilby_pipe_{}".format(args.bilby_pipe_executable))
    call_arg_list = exec_args + unknown_args
    logger.info("Running command: " + " ".join(call_arg_list))
    subprocess.call(call_arg_list)
