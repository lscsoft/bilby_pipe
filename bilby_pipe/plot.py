#!/usr/bin/env python
"""
Module containing the tools for plotting of results
"""
from __future__ import division, print_function

import matplotlib

matplotlib.use("agg")  # noqa
import bilby

from .utils import parse_args, get_command_line_arguments
from .bilbyargparser import BilbyArgParser


def create_parser():
    """ Generate a parser for the plot script

    Returns
    -------
    parser: BilbyArgParser
        A parser with all the default options already added

    """
    parser = BilbyArgParser(ignore_unknown_config_file_keys=True)
    parser.add("--result", type=str, required=True, help="The result file")
    return parser


def main():
    """ Top-level interface for bilby_pipe """
    args, unknown_args = parse_args(get_command_line_arguments(), create_parser())

    result = bilby.gw.result.CBCResult.from_json(args.result)
    result.plot_corner()
    result.plot_marginals()
    result.plot_calibration_posterior()
