#!/usr/bin/env python
"""
Module containing the tools for plotting of results
"""
from __future__ import division, print_function

import matplotlib

matplotlib.use("agg")  # noqa
import bilby

from .utils import DataDump, parse_args, get_command_line_arguments, logger
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

    logger.info("Generating plots for results file {}".format(args.result))

    result = bilby.gw.result.CBCResult.from_json(args.result)
    data_dump = DataDump.from_pickle(result.meta_data["data_dump"])
    outdir = result.outdir
    label = result.label
    result.plot_marginals(priors=True)
    result.plot_calibration_posterior()
    logger.info("Generating source mass corner")
    result.plot_corner(
        ["mass_1_source", "mass_2_source", "chirp_mass_source", "mass_ratio_source"],
        filename="{}/{}_mass_corner.png".format(outdir, label),
    )
    logger.info("Generating distance sky time corner")
    result.plot_corner(
        ["luminosity_distance", "theta_jn", "ra", "dec", "geocent_time"],
        filename="{}/{}_distance-sky-time_corner.png".format(outdir, label),
    )
    logger.info("Generating waveform plots")
    result.plot_waveform_posterior(interferometers=data_dump.interferometers)
    logger.info("Generating skymap")
    result.plot_skymap(maxpts=2000)
