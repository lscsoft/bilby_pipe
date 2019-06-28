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

from bilby_pipe.utils import DataDump, logger, BilbyPipeError, convert_string_to_dict
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
        A list of the arguments to parse. Defauts to `sys.argv[1:]`

    """

    def __init__(self, args, unknown_args):
        logger.info("Command line arguments: {}".format(args))

        self.meta_data = dict()
        self.result = None

        self.ini = args.ini
        self.idx = args.idx
        self.cluster = args.cluster
        self.process = args.process
        self.detectors = args.detectors
        self.prior_file = args.prior_file
        self.deltaT = args.deltaT
        self.reference_frequency = args.reference_frequency
        self.minimum_frequency = args.minimum_frequency
        self.maximum_frequency = args.maximum_frequency
        self.waveform_approximant = args.waveform_approximant
        self.distance_marginalization = args.distance_marginalization
        self.distance_marginalization_lookup_table = (
            args.distance_marginalization_lookup_table
        )
        self.phase_marginalization = args.phase_marginalization
        self.time_marginalization = args.time_marginalization
        self.sampler = args.sampler
        self.sampler_kwargs = args.sampler_kwargs
        self.sampling_seed = args.sampling_seed
        self.outdir = args.outdir
        self.label = args.label
        self.data_label = args.data_label
        self.default_prior = args.default_prior
        self.frequency_domain_source_model = args.frequency_domain_source_model
        self.likelihood_type = args.likelihood_type
        self.roq_folder = args.roq_folder
        self.roq_scale_factor = args.roq_scale_factor
        self.calibration_model = args.calibration_model
        self.spline_calibration_envelope_dict = args.spline_calibration_envelope_dict
        self.spline_calibration_amplitude_uncertainty_dict = (
            args.spline_calibration_amplitude_uncertainty_dict
        )
        self.spline_calibration_phase_uncertainty_dict = (
            args.spline_calibration_phase_uncertainty_dict
        )
        self.spline_calibration_nodes = args.spline_calibration_nodes
        self.periodic_restart_time = args.periodic_restart_time

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
                    "Data analsys script recieved a list of samplers with "
                    "more than one element: {}. Unable to proceed".format(sampler)
                )

    @property
    def sampler_kwargs(self):
        return self._sampler_kwargs

    @sampler_kwargs.setter
    def sampler_kwargs(self, sampler_kwargs):
        if sampler_kwargs is not None:
            self._sampler_kwargs = convert_string_to_dict(
                sampler_kwargs, "sampler-kwargs"
            )
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
    def trigger_time(self):
        return self.data_dump.trigger_time

    @property
    def data_dump(self):
        if hasattr(self, "_data_dump"):
            return self._data_dump

        filename = DataDump.get_filename(
            self.data_directory, self.data_label, str(self.idx)
        )
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
    def parameter_conversion(self):
        if "binary_neutron_star" in self._frequency_domain_source_model:
            return bilby.gw.conversion.convert_to_lal_binary_neutron_star_parameters
        elif "binary_black_hole" in self._frequency_domain_source_model:
            return bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters
        else:
            return None

    @property
    def waveform_generator(self):
        if self.likelihood_type == "GravitationalWaveTransient":
            waveform_generator = bilby.gw.WaveformGenerator(
                sampling_frequency=self.interferometers.sampling_frequency,
                duration=self.interferometers.duration,
                frequency_domain_source_model=self.bilby_frequency_domain_source_model,
                parameter_conversion=self.parameter_conversion,
                start_time=self.interferometers.start_time,
                waveform_arguments=self.waveform_arguments,
            )

        elif self.likelihood_type == "ROQGravitationalWaveTransient":
            logger.info(
                "Using the ROQ likelihood with roq-folder={}".format(self.roq_folder)
            )
            freq_nodes_linear = np.load(self.roq_folder + "/fnodes_linear.npy")
            freq_nodes_quadratic = np.load(self.roq_folder + "/fnodes_quadratic.npy")
            freq_nodes_linear *= self.roq_scale_factor
            freq_nodes_quadratic *= self.roq_scale_factor

            waveform_arguments = self.waveform_arguments.copy()
            waveform_arguments["frequency_nodes_linear"] = freq_nodes_linear
            waveform_arguments["frequency_nodes_quadratic"] = freq_nodes_quadratic

            waveform_generator = bilby.gw.waveform_generator.WaveformGenerator(
                sampling_frequency=self.interferometers.sampling_frequency,
                duration=self.interferometers.duration,
                frequency_domain_source_model=self.bilby_roq_frequency_domain_source_model,
                start_time=self.interferometers.start_time,
                parameter_conversion=self.parameter_conversion,
                waveform_arguments=waveform_arguments,
            )

        else:
            raise ValueError("Unknown likelihood function")

        return waveform_generator

    @property
    def waveform_arguments(self):
        return dict(
            reference_frequency=self.reference_frequency,
            waveform_approximant=self.waveform_approximant,
            minimum_frequency=self.minimum_frequency,
        )

    @property
    def likelihood(self):
        if self.likelihood_type == "GravitationalWaveTransient":
            return bilby.gw.likelihood.GravitationalWaveTransient(
                interferometers=self.interferometers,
                waveform_generator=self.waveform_generator,
                priors=self.priors,
                phase_marginalization=self.phase_marginalization,
                distance_marginalization=self.distance_marginalization,
                distance_marginalization_lookup_table=self.distance_marginalization_lookup_table,
                time_marginalization=self.time_marginalization,
            )

        elif self.likelihood_type == "ROQGravitationalWaveTransient":
            if self.time_marginalization:
                logger.warning(
                    "Time marginalization not implemented for "
                    "ROQGravitationalWaveTransient: option ignored"
                )

            params = np.genfromtxt(self.roq_folder + "/params.dat", names=True)
            self.scale_roq_params(params, scale_factor=self.roq_scale_factor)
            self.test_roq_prior_bounds(params)

            weight_file = os.path.join(
                self.data_directory, self.data_label + "_roq_weights.json"
            )

            logger.info("Loading ROQ weights from {}".format(weight_file))

            return bilby.gw.likelihood.ROQGravitationalWaveTransient(
                interferometers=self.interferometers,
                waveform_generator=self.waveform_generator,
                weights=weight_file,
                priors=self.priors,
                roq_params=params,
                phase_marginalization=self.phase_marginalization,
                distance_marginalization=self.distance_marginalization,
                distance_marginalization_lookup_table=self.distance_marginalization_lookup_table,
            )

        else:
            raise ValueError("Unknown likelihood function")

    def test_roq_prior_bounds(self, params):
        if 'chirp_mass' in self.priors:
            assert (
                params['chirpmass-min'] <= self.priors['chirp_mass'].minimum and
                params['chirpmass-max'] <= self.priors['chirp_mass'].maximum
            ), "Chirp mass bounds exceed ROQ basis range."
        if 'mass_ratio' in self.priors:
            assert (
                    params['q-min'] <= self.priors['mass_ratio'].minimum and
                    params['q-max'] <= self.priors['mass_ratio'].maximum
            ), "Mass ratio bounds exceed ROQ basis range."
        if 'a_1' in self.priors:
            assert (
                    params['chiL1-max'] <= self.priors['a_1'].maximum
            ), "Primary spin magnitude bounds exceed ROQ basis range."
        if 'a_2' in self.priors:
            assert (
                    params['chiL2-max'] <= self.priors['a_2'].maximum
            ), "Secondary spin magnitude bounds exceed ROQ basis range."
        if 'chi_1' in self.priors:
            assert (
                    params['chiL1-min'] <= self.priors['chi_1'].minimum and
                    params['chiL1-max'] <= self.priors['chi_1'].maximum
            ), "Primary spin bounds exceed ROQ basis range."
        if 'chi_2' in self.priors:
            assert (
                    params['chiL2-min'] <= self.priors['chi_2'].minimum and
                    params['chiL2-max'] <= self.priors['chi_2'].maximum
            ), "Secondary spin bounds exceed ROQ basis range."

    @property
    def parameter_generation(self):
        if "binary_neutron_star" in self._frequency_domain_source_model:
            return bilby.gw.conversion.generate_all_bns_parameters
        elif "binary_black_hole" in self._frequency_domain_source_model:
            return bilby.gw.conversion.generate_all_bbh_parameters
        else:
            return None

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

    def run_sampler(self):
        signal.signal(signal.SIGALRM, handler=sighandler)
        signal.alarm(self.periodic_restart_time)
        self.result = bilby.run_sampler(
            likelihood=self.likelihood,
            priors=self.priors,
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
    analysis = DataAnalysisInput(args, unknown_args)
    analysis.run_sampler()
    sys.exit(0)
