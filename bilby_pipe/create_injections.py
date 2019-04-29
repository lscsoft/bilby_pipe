#!/usr/bin/env python
"""
Module containing the tools for creating injection files
"""
from __future__ import division, print_function

import sys
import json

import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("agg")  # noqa
import bilby

from .input import Input
from .utils import parse_args, logger, BilbyPipeError
from .bilbyargparser import BilbyArgParser


def create_parser():
    """ Generate a parser for the create_injections.py script

    Additional options can be added to the returned parser beforing calling
    `parser.parse_args` to generate the arguments`

    Returns
    -------
    parser: BilbyArgParser
        A parser with all the default options already added

    """
    parser = BilbyArgParser(ignore_unknown_config_file_keys=True)
    parser.add("ini", type=str, is_config_file=True, help="The ini file")
    parser.add("--label", type=str, default="LABEL", help="The output label")
    parser.add(
        "--outdir", type=str, default="bilby_outdir", help="The output directory"
    )
    parser.add_arg(
        "--prior-file",
        type=str,
        default=None,
        help="The prior file from which to generate injections",
    )
    parser.add(
        "--default-prior",
        default="BBHPriorDict",
        type=str,
        help="The name of the prior set to base the prior on. Can be one of"
        "[PriorDict, BBHPriorDict, BNSPriorDict, CalibrationPriorDict]",
    )
    parser.add_arg(
        "--n-injection", type=int, help="The number of injections to generate"
    )
    parser.add(
        "--generation-seed",
        default=None,
        type=int,
        help="Random seed used during data generation",
    )
    parser.add(
        "--deltaT",
        type=float,
        default=0.2,
        help=(
            "The symmetric width (in s) around the trigger time to"
            " search over the coalesence time"
        ),
    )
    time_parser = parser.add_mutually_exclusive_group()
    time_parser.add("--trigger-time", default=None, type=float, help="The trigger time")
    time_parser.add(
        "--gps-file",
        default=None,
        type=str,
        help="File containing segment GPS start times",
    )
    parser.add(
        "--duration",
        type=int,
        default=4,
        help="The duration of data around the event to use (only used with gps-file)",
    )
    parser.add(
        "--post-trigger-duration",
        type=float,
        default=2,
        help=(
            "Time (in s) after the trigger_time to the end of the segment "
            "(only used with gps-file)"
        ),
    )

    return parser


class CreateInjectionInput(Input):
    """ An object to hold all the inputs to create_injection

    Parameters
    ----------
    parser: configargparse.ArgParser, optional
        The parser containing the command line / ini file inputs
    args_list: list, optional
        A list of the arguments to parse. Defauts to `sys.argv[1:]`

    """

    def __init__(self, args, unknown_args):
        np.random.seed(args.generation_seed)
        logger.debug("Creating new CreateInjectionInput object")
        logger.info("Command line arguments: {}".format(args))

        self.prior_file = args.prior_file
        self.default_prior = args.default_prior
        self.n_injection = args.n_injection
        self.outdir = args.outdir
        self.label = args.label
        self.trigger_time = args.trigger_time
        self.deltaT = args.deltaT
        self.gps_file = args.gps_file
        self.duration = args.duration
        self.post_trigger_duration = args.post_trigger_duration

    @property
    def n_injection(self):
        """ The number of injections to create """
        if self._n_injection is not None:
            return self._n_injection
        else:
            raise BilbyPipeError("The number of injection has not been set")

    @n_injection.setter
    def n_injection(self, n_injection):
        self._n_injection = n_injection

    def check_and_add_geocent_times_to_injections(self, injection_values):
        """ If injection_values does not include geocent_time, sample them

        If --gps-file is given, the geocent_time prior has to be defined for
        each line. This contains the logic to define the trigger time and
        sample from the geocent_time prior centered on the trigger
        """
        if "geocent_time" in injection_values:
            return injection_values
        else:
            gct = self.gpstimes + self.duration - self.post_trigger_duration
            gct += np.random.uniform(
                -self.deltaT / 2, self.deltaT / 2.0, self.n_injection
            )
            injection_values["geocent_time"] = gct
            return injection_values

    def create_injection_file(self, filename):
        logger.info(
            "Generating injection file with prior={}, n_injection={}".format(
                self.priors, self.n_injection
            )
        )
        injection_values = pd.DataFrame.from_dict(self.priors.sample(self.n_injection))
        injection_values = self.check_and_add_geocent_times_to_injections(
            injection_values
        )
        injections = dict(injections=injection_values)
        with open(filename, "w") as file:
            json.dump(
                injections, file, indent=2, cls=bilby.core.result.BilbyJsonEncoder
            )
        logger.info("Created injection file {}".format(filename))

    def _parse_gps_file(self):
        self.gpstimes = self.read_gps_file()


def main():
    args, unknown_args = parse_args(sys.argv[1:], create_parser())
    inputs = CreateInjectionInput(args, unknown_args)
    inputs.create_injection_file()
