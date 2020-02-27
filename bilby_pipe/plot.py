#!/usr/bin/env python
"""
Module containing the tools for plotting of results
"""
import os

from bilby.core.utils import check_directory_exists_and_if_not_mkdir
from bilby.gw.result import CBCResult
from bilby.gw.source import (
    binary_black_hole_roq,
    binary_neutron_star_roq,
    lal_binary_black_hole,
    lal_binary_neutron_star,
)

from .bilbyargparser import BilbyArgParser
from .utils import DataDump, get_command_line_arguments, logger, parse_args

# fmt: off
import matplotlib  # isort:skip
matplotlib.use("agg")  # noqa
import matplotlib.pyplot as plt  # isort:skip
# fmt: on


def create_parser():
    """ Generate a parser for the plot script

    Returns
    -------
    parser: BilbyArgParser
        A parser with all the default options already added

    """
    parser = BilbyArgParser(ignore_unknown_config_file_keys=True)
    parser.add("--result", type=str, required=True, help="The result file")
    parser.add("--calibration", action="store_true", help="Generate calibration plot")
    parser.add("--corner", action="store_true", help="Generate corner plots")
    parser.add("--marginal", action="store_true", help="Generate marginal plots")
    parser.add("--skymap", action="store_true", help="Generate skymap")
    parser.add("--waveform", action="store_true", help="Generate waveform")
    parser.add(
        "--format",
        type=str,
        default="png",
        help="Format for making bilby_pipe plots, can be [png, pdf, html]. "
        "If specified format is not supported, will default to png.",
    )
    return parser


def _parse_and_load():
    args, unknown_args = parse_args(get_command_line_arguments(), create_parser())

    logger.info("Generating plots for results file {}".format(args.result))

    result = CBCResult.from_json(args.result)
    if "data_dump" in result.meta_data and os.path.exists(
        result.meta_data["data_dump"]
    ):
        data_dump = DataDump.from_pickle(result.meta_data["data_dump"])
    else:
        data_dump = None

    if hasattr(args, "webdir"):
        outdir = os.path.join(args.webdir, "bilby")
    elif hasattr(args, "outdir"):
        outdir = args.outdir
    else:
        outdir = result.outdir
    logger.info("Plots will be made in {}".format(outdir))

    check_directory_exists_and_if_not_mkdir(outdir)
    result.outdir = outdir
    return args, result, data_dump


def plot_calibration():
    args, result, _ = _parse_and_load()

    logger.info("Generating calibration posterior")
    allowed_formats = list(plt.gcf().canvas.get_supported_filetypes())
    if args.plot_format in allowed_formats:
        _format = args.plot_format
    else:
        logger.info(
            "Requested format '{}' not recognised. "
            "Falling back to png.".format(args.format)
        )
        _format = "png"

    result.plot_calibration_posterior(format=_format)


def plot_corner():
    _, result, _ = _parse_and_load()
    logger.info("Generating intrinsic parameter corner")
    result.plot_corner(
        [
            "mass_1_source",
            "mass_2_source",
            "chirp_mass_source",
            "mass_ratio",
            "chi_eff",
            "chi_p",
        ],
        filename="{}/{}_intrinsic_corner.png".format(result.outdir, result.label),
    )
    logger.info("Generating extrinsic parameter corner")
    result.plot_corner(
        ["luminosity_distance", "redshift", "theta_jn", "ra", "dec", "geocent_time"],
        filename="{}/{}_extrinsic_corner.png".format(result.outdir, result.label),
    )


def plot_marginal():
    _, result, _ = _parse_and_load()
    logger.info("Plotting 1d posteriors")
    result.plot_marginals(priors=True)


def plot_skymap():
    _, result, _ = _parse_and_load()
    logger.info("Generating skymap")
    try:
        result.plot_skymap(maxpts=5000)
    except Exception as e:
        logger.info("Unable to generate skymap: error {}".format(e))


def plot_waveform():
    args, result, data_dump = _parse_and_load()
    interferometers = getattr(data_dump, "interferometers", None)
    if result.frequency_domain_source_model == binary_black_hole_roq:
        logger.info(
            "Sampling used the binary_black_hole_roq source model, using "
            "the lal_binary_black_hole_model for the waveform plot."
        )
        result.meta_data["likelihood"][
            "frequency_domain_source_model"
        ] = lal_binary_black_hole
    elif result.frequency_domain_source_model == binary_neutron_star_roq:
        logger.info(
            "Sampling used the binary_neutron_star_roq source model, using "
            "the lal_binary_neutron_star_model for the waveform plot."
        )
        result.meta_data["likelihood"][
            "frequency_domain_source_model"
        ] = lal_binary_neutron_star
    logger.info("Generating waveform posterior")

    allowed_formats = list(plt.gcf().canvas.get_supported_filetypes()) + ["html"]
    if args.format in allowed_formats:
        _format = args.format
    else:
        logger.info(
            "Requested format '{}' not recognised. "
            "Falling back to png.".format(args.format)
        )
        _format = "png"

    result.plot_waveform_posterior(
        interferometers=interferometers, n_samples=1000, format=_format
    )


def main():
    """ Top-level interface for bilby_pipe """

    args, result, data_dump = _parse_and_load()

    if args.skymap:
        plot_skymap()

    if args.marginal:
        plot_marginal()

    if args.corner:
        plot_corner()

    if args.calibration:
        plot_calibration()

    if args.waveform:
        plot_waveform()
