#!/usr/bin/env python
"""
Script to analyse the stored data
"""
from __future__ import division, print_function

import sys
import signal
import os

import numpy as np
import matplotlib

matplotlib.use("agg")  # noqa
import bilby

from bilby_pipe.utils import (
    logger,
    log_version_information,
    BilbyPipeError,
    DataDump,
    convert_string_to_dict,
    SAMPLER_SETTINGS,
)

from bilby_pipe.main import parse_args
from bilby_pipe.parser import create_parser
from bilby_pipe.input import Input


def sighandler(signum, frame):
    logger.info("Performing periodic eviction")
    sys.exit(130)


class DataAnalysisInput(Input):
    """ Handles user-input and analysis of intermediate ifo list

    Parameters
    ----------
    parser: BilbyArgParser, optional
        The parser containing the command line / ini file inputs
    args_list: list, optional
        A list of the arguments to parse. Defaults to `sys.argv[1:]`

    """

    def __init__(self, args, unknown_args, test=False):
        logger.info("Command line arguments: {}".format(args))

        self.meta_data = dict()
        self.result = None

        self.ini = args.ini
        self.idx = args.idx
        self.cluster = args.cluster
        self.process = args.process
        self.detectors = args.detectors

        self.sampler = args.sampler
        self.sampler_kwargs = args.sampler_kwargs
        self.sampling_seed = args.sampling_seed
        self.outdir = args.outdir
        self.label = args.label
        self.data_dump_file = args.data_dump_file

        self.frequency_domain_source_model = args.frequency_domain_source_model
        self.periodic_restart_time = args.periodic_restart_time

        if test is False:
            self._load_data_dump()

    @property
    def cluster(self):
        return self._cluster

    @cluster.setter
    def cluster(self, cluster):
        try:
            self._cluster = int(cluster)
        except (ValueError, TypeError):
            logger.debug("Unable to convert input `cluster` to type int")
            self._cluster = cluster

    @property
    def process(self):
        return self._process

    @process.setter
    def process(self, process):
        try:
            self._process = int(process)
        except (ValueError, TypeError):
            logger.debug("Unable to convert input `process` to type int")
            self._process = process

    @property
    def sampling_seed(self):
        return self._samplng_seed

    @sampling_seed.setter
    def sampling_seed(self, sampling_seed):
        if sampling_seed is None:
            sampling_seed = np.random.randint(1, 1e6)
        self._samplng_seed = sampling_seed
        np.random.seed(sampling_seed)
        logger.info("Sampling seed set to {}".format(sampling_seed))

        if self.sampler == "cpnest":
            self.sampler_kwargs["seed"] = self.sampler_kwargs.get(
                "seed", self._samplng_seed
            )

    @property
    def sampler(self):
        return self._sampler

    @sampler.setter
    def sampler(self, sampler):
        """ Setter for the sampler

        By default, the input parser takes a list of samplers (to enable DAGs
        to be specified to run over all the samplers). In the analysis script,
        it must be given only a single sampler. This logic checks that is the
        case and raises an error otherwise
        """
        if isinstance(sampler, str):
            self._sampler = sampler
        elif isinstance(sampler, list):
            if len(sampler) == 1:
                self._sampler = sampler[0]
            else:
                raise BilbyPipeError(
                    "Data analysis script received a list of samplers with "
                    "more than one element: {}. Unable to proceed".format(sampler)
                )

    @property
    def sampler_kwargs(self):
        return self._sampler_kwargs

    @sampler_kwargs.setter
    def sampler_kwargs(self, sampler_kwargs):
        if sampler_kwargs is not None:
            if sampler_kwargs.lower() == "default":
                self._sampler_kwargs = SAMPLER_SETTINGS["Default"]
            elif sampler_kwargs.lower() == "fasttest":
                self._sampler_kwargs = SAMPLER_SETTINGS["FastTest"]
            else:
                self._sampler_kwargs = convert_string_to_dict(
                    sampler_kwargs, "sampler-kwargs"
                )
        else:
            self._sampler_kwargs = dict()

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
            self.print_detector_information(self._interferometers)
            return self._interferometers

    @staticmethod
    def print_detector_information(interferometers):
        for ifo in interferometers:
            logger.info(
                "{}: sampling-frequency={}, segment-start-time={}, duration={}".format(
                    ifo.name,
                    ifo.strain_data.sampling_frequency,
                    ifo.strain_data.start_time,
                    ifo.strain_data.duration,
                )
            )

    @property
    def data_dump(self):
        if hasattr(self, "_data_dump"):
            return self._data_dump
        else:
            raise BilbyPipeError("Data dump not loaded")

    def _load_data_dump(self):
        filename = self.data_dump_file
        self.meta_data["data_dump"] = filename

        logger.debug("Data dump not previously loaded")

        if os.path.isfile(filename):
            pass
        elif os.path.isfile(os.path.basename(filename)):
            filename = os.path.basename(filename)
        else:
            raise FileNotFoundError(
                "No dump data {} file found. Most likely the generation "
                "step failed".format(filename)
            )

        self._data_dump = DataDump.from_pickle(filename)
        self.meta_data.update(self._data_dump.meta_data)
        return self._data_dump

    @property
    def result_class(self):
        """ The bilby result class to store results in """
        try:
            return bilby.gw.result.CompactBinaryCoalescenceResult
        except AttributeError:
            logger.debug("Unable to use CBC specific result class")
            return None

    @property
    def result_directory(self):
        result_dir = os.path.join(self.outdir, "result")
        return os.path.relpath(result_dir)

    def get_likelihood_and_priors(self):
        """ Read in the like and prior from the data dump, down select for detectors """
        priors = self.data_dump.priors
        likelihood = self.data_dump.likelihood

        likelihood.interferometers = self.interferometers

        interferometer_names = [ifo.name for ifo in self.interferometers]
        priors_copy = priors.copy()
        for prior in priors:
            if "recalib" in prior:
                detector = prior.split("_")[1]
                if detector not in interferometer_names:
                    logger.debug(
                        "Removing prior {} from priors: not in detector list".format(
                            prior
                        )
                    )
                    priors_copy.pop(prior)
        return likelihood, priors_copy

    def run_sampler(self):
        signal.signal(signal.SIGALRM, handler=sighandler)
        signal.alarm(self.periodic_restart_time)

        likelihood, priors = self.get_likelihood_and_priors()

        self.result = bilby.run_sampler(
            likelihood=likelihood,
            priors=priors,
            sampler=self.sampler,
            label=self.label,
            outdir=self.result_directory,
            conversion_function=self.parameter_generation,
            injection_parameters=self.meta_data["injection_parameters"],
            meta_data=self.meta_data,
            result_class=self.result_class,
            **self.sampler_kwargs,
        )


def create_analysis_parser():
    return create_parser(top_level=False)


def main():
    args, unknown_args = parse_args(sys.argv[1:], create_analysis_parser())
    log_version_information()
    analysis = DataAnalysisInput(args, unknown_args)
    analysis.run_sampler()
    sys.exit(0)
