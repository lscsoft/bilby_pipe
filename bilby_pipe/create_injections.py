#!/usr/bin/env python
"""
Module containing the tools for creating injection files
"""
from __future__ import division, print_function

import sys

import bilby
from bilby.gw.prior import BBHPriorDict
import deepdish
import pandas as pd

from bilby_pipe.utils import logger
from bilby_pipe.main import parse_args, Input
from bilby_pipe.bilbyargparser import BilbyArgParser


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
    parser.add('ini', type=str, is_config_file=True, help='The ini file')
    parser.add('--label', type=str, default='LABEL',
               help='The output label')
    parser.add('--outdir', type=str, default='bilby_outdir',
               help='The output directory')
    parser.add_arg('--prior-file', type=str, default=None,
                   help='The prior file from which to generate injections')
    parser.add_arg('--n-injection', type=int,
                   help='The number of injections to generate')
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
        logger.debug('Creating new CreateInjectionInput object')
        logger.info('Command line arguments: {}'.format(args))

        self.prior_file = args.prior_file
        self.n_injection = args.n_injection
        self.outdir = args.outdir
        self.label = args.label

    @property
    def n_injection(self):
        """ The number of injections to create """
        if self._n_injection is not None:
            return self._n_injection
        else:
            raise ValueError("The number of injection has not been set")

    @n_injection.setter
    def n_injection(self, n_injection):
        self._n_injection = n_injection

    @property
    def prior_file(self):
        if self._prior_file is not None:
            return self._prior_file
        else:
            raise ValueError("The prior_file has not been set")

    @prior_file.setter
    def prior_file(self, prior_file):
        if isinstance(prior_file, str):
            logger.debug("Setting prior_file to {}".format(prior_file))
            self._prior_file = prior_file
            logger.debug("Generating PriorDict")
            self.prior = BBHPriorDict(filename=self._prior_file)
        else:
            raise ValueError("Type of prior_file must be str")

    @property
    def prior(self):
        try:
            return self._prior
        except AttributeError:
            raise ValueError("The prior has not been set")

    @prior.setter
    def prior(self, prior):
        if isinstance(prior, bilby.core.prior.PriorDict):
            self._prior = prior
        else:
            raise ValueError("Input prior not understood")

    def create_injection_file(self, filename):
        logger.info("Generating injection file with prior={}, n_injection={}"
                    .format(self.prior, self.n_injection))
        injection_values = pd.DataFrame.from_dict(self.prior.sample(self.n_injection))
        injections = dict(injections=injection_values, prior=self.prior.__repr__)
        deepdish.io.save(filename, injections)
        logger.info("Created injection file {}".format(filename))


def main():
    args, unknown_args = parse_args(sys.argv[1:], create_parser())
    inputs = CreateInjectionInput(args, unknown_args)
    inputs.create_injection_file()
