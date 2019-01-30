#!/usr/bin/env python
"""
Script to analyse the stored data
"""
from __future__ import division, print_function

import sys
import os

import numpy as np
import bilby

from bilby_pipe.utils import logger, BilbyPipeError
from bilby_pipe.main import DataDump, parse_args
from bilby_pipe.parser import create_parser
from bilby_pipe.input import Input


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
        self.idx = args.idx
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
        self.data_label = args.data_label
        self.default_prior = args.default_prior
        self.frequency_domain_source_model = args.frequency_domain_source_model
        self.result = None

    @property
    def cluster(self):
        return self._cluster

    @cluster.setter
    def cluster(self, cluster):
        try:
            self._cluster = int(cluster)
        except (ValueError, TypeError):
            logger.debug('Unable to convert input `cluster` to type int')
            self._cluster = cluster

    @property
    def process(self):
        return self._process

    @process.setter
    def process(self, process):
        try:
            self._process = int(process)
        except (ValueError, TypeError):
            logger.debug('Unable to convert input `process` to type int')
            self._process = process

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
        return self._sampler_kwargs

    @sampler_kwargs.setter
    def sampler_kwargs(self, sampler_kwargs):
        if sampler_kwargs is not None:
            try:
                self._sampler_kwargs = eval(sampler_kwargs)
            except (NameError, TypeError) as e:
                raise BilbyPipeError(
                    "Error {}. Unable to parse sampler_kwargs: {}"
                    .format(e, sampler_kwargs))
        else:
            self._sampler_kwargs = None

    @property
    def interferometers(self):
        try:
            return self._interferometers
        except AttributeError:
            ifos = self.data_dump.interferometers
            names = [ifo.name for ifo in ifos]
            logger.info("Found data for detectors = {}".format(names))
            ifos_to_use = [ifo for ifo in ifos if ifo.name in self.detectors]
            names_to_use = [ifo.name for ifo in ifos_to_use]
            logger.info("Using data for detectors = {}".format(names_to_use))
            self._interferometers = bilby.gw.detector.InterferometerList(ifos_to_use)
            return self._interferometers

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
                '_'.join([self.data_label, str(self.idx), 'data_dump.h5']))
            self._data_dump = DataDump.from_hdf5(filename)
            return self._data_dump

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
        if 'binary_neutron_star' in self._frequency_domain_source_model:
            return bilby.gw.conversion.convert_to_lal_binary_neutron_star_parameters
        elif 'binary_black_hole' in self._frequency_domain_source_model:
            return bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters
        else:
            return None

    @property
    def waveform_generator(self):
        waveform_generator = bilby.gw.WaveformGenerator(
            sampling_frequency=self.interferometers.sampling_frequency,
            duration=self.interferometers.duration,
            frequency_domain_source_model=self.bilby_frequency_domain_source_model,
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
    def parameter_generation(self):
        if 'binary_neutron_star' in self._frequency_domain_source_model:
            return bilby.gw.conversion.generate_all_bns_parameters
        elif 'binary_black_hole' in self._frequency_domain_source_model:
            return bilby.gw.conversion.generate_all_bbh_parameters
        else:
            return None

    def run_sampler(self):
        self.result = bilby.run_sampler(
            likelihood=self.likelihood, priors=self.priors,
            sampler=self.sampler, label=self.label, outdir=self.result_directory,
            conversion_function=self.parameter_generation,
            injection_parameters=self.data_dump.meta_data['injection_parameters'],
            **self.sampler_kwargs)


def create_analysis_parser():
    return create_parser(pipe_args=False, job_args=True, run_spec=True,
                         pe_summary=False, injection=False, data_gen=False,
                         waveform=True, generation=False, analysis=True)


def main():
    args, unknown_args = parse_args(sys.argv[1:], create_analysis_parser())
    analysis = DataAnalysisInput(args, unknown_args)
    analysis.run_sampler()
    if args.create_plots:
        analysis.result.plot_corner()
        analysis.result.plot_marginals()
