#!/usr/bin/env python
""" Script to perform data analysis """
import os
import signal
import sys

import numpy as np

import bilby
from bilby_pipe.input import Input
from bilby_pipe.main import parse_args
from bilby_pipe.parser import create_parser
from bilby_pipe.utils import (
    CHECKPOINT_EXIT_CODE,
    BilbyPipeError,
    DataDump,
    log_version_information,
    logger,
)

# fmt: off
import matplotlib  # isort:skip
matplotlib.use("agg")
# fmt: on


def sighandler(signum, frame):
    logger.info("Performing periodic eviction")
    sys.exit(CHECKPOINT_EXIT_CODE)


class DataAnalysisInput(Input):
    """Handles user-input for the data analysis script

    Parameters
    ----------
    parser: BilbyArgParser, optional
        The parser containing the command line / ini file inputs
    args_list: list, optional
        A list of the arguments to parse. Defaults to `sys.argv[1:]`

    """

    def __init__(self, args, unknown_args, test=False):
        logger.info(f"Command line arguments: {args}")

        # Generic initialisation
        self.meta_data = dict()
        self.result = None

        # Admin arguments
        self.ini = args.ini
        self.scheduler = args.scheduler
        self.periodic_restart_time = args.periodic_restart_time
        self.request_cpus = args.request_cpus

        # Naming arguments
        self.outdir = args.outdir
        self.label = args.label

        # Data dump file to run on
        self.data_dump_file = args.data_dump_file

        # Choices for running
        self.detectors = args.detectors
        self.sampler = args.sampler
        self.sampler_kwargs = args.sampler_kwargs
        self.sampling_seed = args.sampling_seed

        # Frequencies
        self.sampling_frequency = args.sampling_frequency
        self.minimum_frequency = args.minimum_frequency
        self.maximum_frequency = args.maximum_frequency
        self.reference_frequency = args.reference_frequency

        # Waveform, source model and likelihood
        self.waveform_generator_class = args.waveform_generator
        self.waveform_approximant = args.waveform_approximant
        self.catch_waveform_errors = args.catch_waveform_errors
        self.pn_spin_order = args.pn_spin_order
        self.pn_tidal_order = args.pn_tidal_order
        self.pn_phase_order = args.pn_phase_order
        self.pn_amplitude_order = args.pn_amplitude_order
        self.mode_array = args.mode_array
        self.waveform_arguments_dict = args.waveform_arguments_dict
        self.numerical_relativity_file = args.numerical_relativity_file
        self.frequency_domain_source_model = args.frequency_domain_source_model
        self.conversion_function = args.conversion_function
        self.generation_function = args.generation_function
        self.likelihood_type = args.likelihood_type
        self.reference_frame = args.reference_frame
        self.time_reference = args.time_reference
        self.extra_likelihood_kwargs = args.extra_likelihood_kwargs

        # ROQ
        self.roq_folder = args.roq_folder
        self.roq_scale_factor = args.roq_scale_factor

        # Calibration
        self.calibration_model = args.calibration_model
        self.spline_calibration_nodes = args.spline_calibration_nodes
        self.spline_calibration_envelope_dict = args.spline_calibration_envelope_dict

        # Marginalization
        self.distance_marginalization = args.distance_marginalization
        self.distance_marginalization_lookup_table = None
        self.phase_marginalization = args.phase_marginalization
        self.time_marginalization = args.time_marginalization
        self.jitter_time = args.jitter_time

        # Prior conversions
        self.convert_to_flat_in_component_mass = args.convert_to_flat_in_component_mass

        if test is False:
            self._load_data_dump()

    @property
    def sampling_seed(self):
        return self._samplng_seed

    @sampling_seed.setter
    def sampling_seed(self, sampling_seed):
        if sampling_seed is None:
            sampling_seed = np.random.randint(1, 1e6)
        self._samplng_seed = sampling_seed
        np.random.seed(sampling_seed)
        logger.info(f"Sampling seed set to {sampling_seed}")

        if self.sampler == "cpnest":
            self.sampler_kwargs["seed"] = self.sampler_kwargs.get(
                "seed", self._samplng_seed
            )

    @property
    def interferometers(self):
        try:
            return self._interferometers
        except AttributeError:
            ifos = self.data_dump.interferometers
            names = [ifo.name for ifo in ifos]
            logger.info(f"Found data for detectors = {names}")
            ifos_to_use = [ifo for ifo in ifos if ifo.name in self.detectors]
            names_to_use = [ifo.name for ifo in ifos_to_use]
            logger.info(f"Using data for detectors = {names_to_use}")
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
        """Read in the likelihood and prior from the data dump

        This reads in the data dump values and reconstructs the likelihood and
        priors. Note, care must be taken to use the "search_priors" which differ
        from the true prior when using marginalization

        Returns
        -------
        likelihood, priors
            The bilby likelihood and priors
        """

        priors = self.data_dump.priors_class(self.data_dump.priors_dict)
        self.priors = priors

        self.likelihood_lookup_table = self.data_dump.likelihood_lookup_table
        self.likelihood_roq_weights = self.data_dump.likelihood_roq_weights
        self.likelihood_roq_params = self.data_dump.likelihood_roq_params

        likelihood = self.likelihood
        priors = self.search_priors
        return likelihood, priors

    def run_sampler(self):
        if self.scheduler.lower() == "condor":
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
            exit_code=CHECKPOINT_EXIT_CODE,
            **self.sampler_kwargs,
        )

        if self.convert_to_flat_in_component_mass:
            try:
                result_reweighted = (
                    bilby.gw.prior.convert_to_flat_in_component_mass_prior(self.result)
                )
                result_reweighted.save_to_file()
            except Exception as e:
                logger.warning(
                    f"Unable to convert to the flat in component mass prior due to: {e}"
                )


def create_analysis_parser():
    """ Data analysis parser creation """
    return create_parser(top_level=False)


def main():
    """ Data analysis main logic """
    args, unknown_args = parse_args(sys.argv[1:], create_analysis_parser())
    log_version_information()
    analysis = DataAnalysisInput(args, unknown_args)
    analysis.run_sampler()
    sys.exit(0)
