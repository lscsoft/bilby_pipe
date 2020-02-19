#!/usr/bin/env python
"""
This a command line tool for the generation of injection files for consumption
by bilby_pipe. Injection files can be generated in a variety of formats, see
below, and are generated from a bilby-style prior_file.

Formats
-------
dat: A dat file consists of a space-separated list of parameters with a header.
     For example:

     mass_1 mass_2 luminosity_distance ...
     30 20 1500 ...
     25 12 2000 ...

json: A JSON formatted file

If a geocent_time prior is given in the file, this will be used to create the
time prior. Otherwise, the trigger-time & deltaT or gps-time and deltaT options
are used (see below).
"""
from __future__ import division, print_function

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

import bilby

from .input import Input
from .utils import (
    BilbyPipeError,
    check_directory_exists_and_if_not_mkdir,
    get_geocent_time_with_uncertainty,
    logger,
    parse_args,
)

# fmt: off
import matplotlib  # isort:skip
matplotlib.use("agg")
# fmt: on


class BilbyPipeCreateInjectionsError(BilbyPipeError):
    def __init__(self, message):
        super().__init__(message)


def create_parser():
    """ Generate a parser for the create_injections.py script

    Additional options can be added to the returned parser before calling
    `parser.parse_args` to generate the arguments`

    Returns
    -------
    parser: BilbyArgParser
        A parser with all the default options already added

    """
    parser = argparse.ArgumentParser(
        prog="bilby_pipe_create_injection_file", description=__doc__
    )
    parser.add_arg(
        "prior_file",
        type=str,
        default=None,
        help="The prior file from which to generate injections",
    )
    parser.add("-f", "--filename", type=str, default="injection")
    parser.add_arg(
        "-e",
        "--extension",
        type=str,
        default="dat",
        choices=["json", "dat"],
        help="Prior file format",
    )
    parser.add_arg(
        "-n",
        "--n-injection",
        type=int,
        default=None,
        help="The number of injections to generate: not required if --gps-file is also given",
        required=False,
    )
    parser.add_arg(
        "-t",
        "--trigger-time",
        type=int,
        default=0,
        help=(
            "The trigger time to use for setting a geocent_time prior "
            "(default=0). Ignored if a geocent_time prior exists in the "
            "prior_file or --gps-file is given."
        ),
    )
    parser.add_arg(
        "-g",
        "--gps-file",
        type=str,
        default=None,
        help=(
            "A list of gps start times to use for setting a geocent_time prior"
            ". Note, the trigger time is obtained from "
            " start_time + duration - post_trigger_duration."
        ),
    )
    parser.add(
        "--deltaT",
        type=float,
        default=0.2,
        help=(
            "The symmetric width (in s) around the trigger time to"
            " search over the coalesence time. Ignored if a geocent_time prior"
            " exists in the prior_file"
        ),
    )
    parser.add_arg(
        "--post-trigger-duration",
        type=float,
        default=2,
        help=(
            "The post trigger duration (default=2s), used only in conjunction "
            "with --gps-file"
        ),
    )
    parser.add_arg(
        "--duration",
        type=float,
        default=4,
        help=(
            "The segment duration (default=4s), used only in conjunction with "
            "--gps-file"
        ),
    )
    parser.add(
        "-s",
        "--generation-seed",
        default=None,
        type=int,
        help="Random seed used during data generation",
    )
    parser.add(
        "--default-prior",
        default="BBHPriorDict",
        type=str,
        help="The name of the prior set to base the prior on. Can be one of"
        "[PriorDict, BBHPriorDict, BNSPriorDict, CalibrationPriorDict]",
    )
    return parser


class PriorFileInput(Input):
    """ An object to hold inputs to create_injection for consistency"""

    def __init__(
        self,
        prior_file,
        prior_dict,
        default_prior,
        trigger_time,
        deltaT,
        gps_file,
        duration,
        post_trigger_duration,
    ):
        self.prior_file = prior_file
        self.prior_dict = prior_dict
        self.default_prior = default_prior
        self.trigger_time = trigger_time
        self.deltaT = deltaT
        self.gps_file = gps_file
        self.duration = duration
        self.post_trigger_duration = post_trigger_duration


def get_full_path(filename, extension):
    ext_in_filename = os.path.splitext(filename)[1].lstrip(".")
    if ext_in_filename == "":
        path = "{}.{}".format(filename, extension)
    elif ext_in_filename == extension:
        path = filename
    else:
        logger.debug("Overwriting given extension name")
        path = filename
        extension = ext_in_filename
    return path, extension


def create_injection_file(
    filename,
    n_injection,
    prior_file=None,
    prior_dict=None,
    trigger_time=None,
    deltaT=0.2,
    gps_file=None,
    duration=4,
    post_trigger_duration=2,
    generation_seed=None,
    extension="dat",
    default_prior="BBHPriorDict",
):
    path, extension = get_full_path(filename, extension)
    outdir = os.path.dirname(path)
    if outdir != "":
        check_directory_exists_and_if_not_mkdir(outdir)

    prior_file_input = PriorFileInput(
        prior_file=prior_file,
        prior_dict=prior_dict,
        default_prior=default_prior,
        trigger_time=trigger_time,
        deltaT=deltaT,
        gps_file=gps_file,
        duration=duration,
        post_trigger_duration=post_trigger_duration,
    )
    prior_file = prior_file_input.prior_file

    if prior_file is None and prior_dict is None:
        raise BilbyPipeCreateInjectionsError("No prior_file or prior_dict given")

    np.random.seed(generation_seed)
    logger.info("Setting generation seed={}".format(generation_seed))

    if prior_file_input.gps_file is not None:
        logger.info("Generation injection using gps_file {}".format(gps_file))
        if n_injection is not None:
            logger.warning("n-injection given with gps_file, ignoring n-injection")
        n_injection = len(prior_file_input.gpstimes)

    if isinstance(n_injection, int) is False or n_injection < 1:
        raise BilbyPipeCreateInjectionsError(
            "n_injection={}, but must be a positive integer".format(n_injection)
        )

    logger.info(
        "Generating injection file {} from prior={}, n_injection={}".format(
            path, prior_file, n_injection
        )
    )

    priors = prior_file_input.priors
    if prior_file_input.gps_file is not None:
        injection_values = []
        for start_time in prior_file_input.gpstimes:
            geocent_time = get_geocent_time_with_uncertainty(
                geocent_time=start_time + duration - post_trigger_duration,
                uncertainty=prior_file_input.deltaT / 2.0,
            )
            injection_values.append(geocent_time)
        injection_values = pd.DataFrame(injection_values)
    else:
        injection_values = pd.DataFrame.from_dict(priors.sample(n_injection))

    if extension == "json":
        injections = dict(injections=injection_values)
        with open(path, "w") as file:
            json.dump(
                injections, file, indent=2, cls=bilby.core.result.BilbyJsonEncoder
            )
    elif extension == "dat":
        injection_values.to_csv(path, index=False, header=True, sep=" ")
    else:
        raise BilbyPipeCreateInjectionsError(
            "Extension {} not implemented".format(extension)
        )
    logger.info("Created injection file {}".format(path))


def main():
    args, unknown_args = parse_args(sys.argv[1:], create_parser())
    create_injection_file(
        filename=args.filename,
        prior_file=args.prior_file,
        prior_dict=args.prior_dict,
        n_injection=args.n_injection,
        trigger_time=args.trigger_time,
        deltaT=args.deltaT,
        gps_file=args.gps_file,
        duration=args.duration,
        post_trigger_duration=args.post_trigger_duration,
        generation_seed=args.generation_seed,
        extension=args.extension,
    )
