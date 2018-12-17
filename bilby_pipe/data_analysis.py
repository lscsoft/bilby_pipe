#!/usr/bin/env python
"""
Script to analyse the stored data
"""
from __future__ import division, print_function

import sys
import os

import numpy as np
import bilby

from bilby_pipe.utils import logger
from bilby_pipe import webpages
from bilby_pipe.main import Input, DataDump, parse_args
from bilby_pipe.bilbyargparser import BilbyArgParser


def create_parser():
    """ Generate a parser for the data_analysis.py script

    Additional options can be added to the returned parser before calling
    `parser.parse_args` to generate the arguments`

    Returns
    -------
    parser: BilbyArgParser
        A parser with all the default options already added

    """
    parser = BilbyArgParser(ignore_unknown_config_file_keys=True)
    parser.add('--ini', is_config_file=True, help='The ini-style config file')
    parser.add('--cluster', type=int,
               help='The condor cluster ID', default=None)
    parser.add('--process', type=int,
               help='The condor process ID', default=None)
    parser.add(
        '--detectors', action='append',
        help=('The names of detectors to analyse. If given in the ini file, '
              'multiple detectors are specified by `detectors=[H1, L1]`. If '
              'given at the command line, as `--detectors H1 --detectors L1`'))
    parser.add("--prior-file", default=None, help="The prior file")
    parser.add("--deltaT", type=float, default=0.1,
               help=("The symmetric width (in s) around the trigger time to"
                     " search over the coalesence time"))
    parser.add('--reference-frequency', default=20, type=float,
               help="The reference frequency")
    parser.add('--waveform-approximant', default='IMRPhenomPv2', type=str,
               help="The name of the waveform approximant")
    parser.add('--default-prior', default='BBHPriorDict', type=str,
               help="The name of the prior set to base the prior on. Can be one of"
                    "[PriorDict, BBHPriorDict, BNSPriorDict, CalibrationPriorDict]")
    parser.add('--conversion', default='convert_to_lal_binary_black_hole_parameters',
               type=str, help='Name of the conversion function. Can be one of '
                              '[convert_to_lal_binary_black_hole_parameters,'
                              'convert_to_lal_binary_neutron_star_parameters]')
    parser.add('--frequency-domain-source-model', default='lal_binary_black_hole',
               type=str, help="Name of the frequency domain source model. Can be one of"
                              "[lal_binary_black_hole, lal_binary_neutron_star,"
                              "lal_eccentric_binary_black_hole_no_spins, sinegaussian, "
                              "supernova, supernova_pca_model]")
    parser.add(
        '--distance-marginalization', action='store_true', default=False,
        help='Boolean. If true, use a distance-marginalized likelihood')
    parser.add(
        '--phase-marginalization', action='store_true', default=False,
        help='Boolean. If true, use a phase-marginalized likelihood')
    parser.add(
        '--time-marginalization', action='store_true', default=False,
        help='Boolean. If true, use a time-marginalized likelihood')
    parser.add('--sampler', default=None)
    parser.add('--sampler-kwargs', default=None)
    parser.add('--outdir', default='.', help='Output directory')
    parser.add('--label', default='label', help='Output label')
    parser.add('--sampling-seed', default=None, type=int, help='Random sampling seed')
    parser.add('--create-output', default=True, type=bool, help='If true, create plots')
    return parser


class DataAnalysisInput(Input):
    """ Handles user-input and analysis of intermediate ifo list

    Parameters
    ----------
    parser: BilbyArgParser, optional
        The parser containing the command line / ini file inputs
    args_list: list, optional
        A list of the arguments to parse. Defauts to `sys.argv[1:]`

    """

    def __init__(self, args, unknown_args):
        logger.info('Command line arguments: {}'.format(args))

        self.ini = args.ini
        self.cluster = args.cluster
        self.process = args.process
        self.detectors = args.detectors
        self.prior_file = args.prior_file
        self._priors = None
        self.deltaT = args.deltaT
        self.reference_frequency = args.reference_frequency
        self.waveform_approximant = args.waveform_approximant
        self.distance_marginalization = args.distance_marginalization
        self.phase_marginalization = args.phase_marginalization
        self.time_marginalization = args.time_marginalization
        self.sampling_seed = args.sampling_seed
        self.sampler = args.sampler
        self.sampler_kwargs = args.sampler_kwargs
        self.outdir = args.outdir
        self.label = args.label
        self.default_prior = args.default_prior
        self._frequency_domain_source_model = args.frequency_domain_source_model
        self.conversion = args.conversion
        self.result = None

    @property
    def reference_frequency(self):
        return self._reference_frequency

    @reference_frequency.setter
    def reference_frequency(self, reference_frequency):
        self._reference_frequency = float(reference_frequency)

    @property
    def sampling_seed(self):
        return self._samplng_seed

    @sampling_seed.setter
    def sampling_seed(self, sampling_seed):
        if sampling_seed is None:
            sampling_seed = np.random.randint(1, 1e6)
        self._samplng_seed = sampling_seed
        np.random.seed(sampling_seed)
        logger.info('Sampling seed set to {}'.format(sampling_seed))

    @property
    def sampler_kwargs(self):
        if hasattr(self, '_sampler_kwargs'):
            return self._sampler_kwargs
        else:
            return None

    @sampler_kwargs.setter
    def sampler_kwargs(self, sampler_kwargs):
        if sampler_kwargs is not None:
            try:
                self._sampler_kwargs = eval(sampler_kwargs)
            except (NameError, TypeError) as e:
                raise ValueError(
                    "Error {}. Unable to parse sampler_kwargs: {}"
                    .format(e, sampler_kwargs))
        else:
            self._sampler_kwargs = None

    @property
    def interferometers(self):
        return self.data_dump.interferometers

    @property
    def meta_data(self):
        return self.data_dump.meta_data

    @property
    def trigger_time(self):
        return self.data_dump.trigger_time

    @property
    def data_dump(self):
        try:
            return self._data_dump
        except AttributeError:
            filename = os.path.join(
                self.data_directory,
                '_'.join([self.label, str(self.process), 'data_dump.h5']))
            self._data_dump = DataDump.from_hdf5(filename)
            return self._data_dump

    @property
    def run_label(self):
        label = '{}_{}_{}_{}'.format(
            self.label, ''.join(self.detectors), self.sampler, self.process)
        return label

    @property
    def priors(self):
        if self._priors is None:
            if self.default_prior in bilby.core.prior.__dict__.keys():
                self._priors = bilby.core.prior.__dict__[self.default_prior](
                    filename=self.prior_file
                )
            elif self.default_prior in bilby.gw.prior.__dict__.keys():
                self._priors = bilby.gw.prior.__dict__[self.default_prior](
                    filename=self.prior_file
                )
            else:
                logger.info("No prior {} found.").format(self.default_prior)
                logger.info("Defaulting to BBHPriorDict")
                self._priors = bilby.gw.prior.BBHPriorDict(
                    filename=self.prior_file
                )
            if isinstance(self._priors, (bilby.gw.prior.BBHPriorDict, bilby.gw.prior.BNSPriorDict)):
                self._priors['geocent_time'] = bilby.core.prior.Uniform(
                    minimum=self.trigger_time - self.deltaT / 2,
                    maximum=self.trigger_time + self.deltaT / 2,
                    name='geocent_time', latex_label='$t_c$', unit='$s$')
        return self._priors

    @property
    def parameter_conversion(self):
        if self.conversion in bilby.gw.conversion.__dict__.keys():
            return bilby.gw.conversion.__dict__[self.conversion]
        else:
            logger.info("No conversion model {} found.").format(self.conversion)
            logger.info("Defaulting to convert_to_lal_binary_black_hole_parameters")
            return bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters

    @property
    def waveform_generator(self):
        waveform_generator = bilby.gw.WaveformGenerator(
            sampling_frequency=self.interferometers.sampling_frequency,
            duration=self.interferometers.duration,
            frequency_domain_source_model=self.frequency_domain_source_model,
            parameter_conversion=self.parameter_conversion,
            start_time=self.interferometers.start_time,
            waveform_arguments=self.waveform_arguments)
        return waveform_generator

    @property
    def waveform_arguments(self):
        return dict(
            reference_frequency=self.reference_frequency,
            waveform_approximant=self.waveform_approximant,
            minimum_frequency=self.interferometers[0].minimum_frequency)  # FIXME

    @property
    def likelihood(self):
        return bilby.gw.likelihood.GravitationalWaveTransient(
            interferometers=self.interferometers,
            waveform_generator=self.waveform_generator, priors=self.priors,
            phase_marginalization=self.phase_marginalization,
            distance_marginalization=self.distance_marginalization,
            time_marginalization=self.time_marginalization)

    @property
    def frequency_domain_source_model(self):
        if self._frequency_domain_source_model in bilby.gw.source.__dict__.keys():
            return bilby.gw.source.__dict__[self._frequency_domain_source_model]
        else:
            logger.error(
                "No source model {} found.".format(self._frequency_domain_source_model))
            logger.error("Defaulting to lal_binary_black_hole")
            return bilby.gw.source.lal_binary_black_hole

    def run_sampler(self):
        self.result = bilby.run_sampler(
            likelihood=self.likelihood, priors=self.priors,
            sampler=self.sampler, label=self.run_label, outdir=self.result_directory,
            conversion_function=bilby.gw.conversion.generate_all_bbh_parameters,
            injection_parameters=self.data_dump.meta_data['injection_parameters'],
            **self.sampler_kwargs)


def main():
    args, unknown_args = parse_args(sys.argv[1:], create_parser())
    analysis = DataAnalysisInput(args, unknown_args)
    analysis.run_sampler()
    if args.create_output:
        webpages.create_run_output(analysis.result)
