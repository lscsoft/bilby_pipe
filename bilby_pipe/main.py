#!/usr/bin/env python
"""
bilby_pipe is a command line tools for taking user input (as command line
arguments or an ini file) and creating DAG files for submitting bilby parameter
estimation jobs. To get started, write an ini file `config.ini` and run

$ bilby_pipe config.ini

Instruction for how to submit the job are printed in a log message. You can
also specify extra arguments from the command line, e.g.

$ bilby_pipe config.ini --submit

will build and submit the job.
"""
import json
import os

import numpy as np
import pandas as pd

from .create_injections import create_injection_file
from .input import Input
from .job_creation import generate_dag
from .parser import create_parser
from .utils import (
    BilbyPipeError,
    get_command_line_arguments,
    get_outdir_name,
    log_version_information,
    logger,
    parse_args,
    request_memory_generation_lookup,
    tcolors,
)


class MainInput(Input):
    """ An object to hold all the inputs to bilby_pipe"""

    def __init__(self, args, unknown_args):
        logger.debug("Creating new Input object")
        logger.debug(f"Command line arguments: {args}")

        self.known_args = args
        self.unknown_args = unknown_args
        self.ini = args.ini
        self.submit = args.submit
        self.condor_job_priority = args.condor_job_priority
        self.online_pe = args.online_pe
        self.create_plots = args.create_plots
        self.singularity_image = args.singularity_image
        self.create_summary = args.create_summary

        self.outdir = args.outdir
        self.label = args.label
        self.log_directory = args.log_directory
        self.accounting = args.accounting
        self.sampler = args.sampler
        self.detectors = args.detectors
        self.coherence_test = args.coherence_test
        self.n_parallel = args.n_parallel
        self.transfer_files = args.transfer_files
        self.osg = args.osg
        self.analysis_executable = args.analysis_executable
        self.result_format = args.result_format

        self.webdir = args.webdir
        self.email = args.email
        self.notification = args.notification
        self.existing_dir = args.existing_dir

        self.scheduler = args.scheduler
        self.scheduler_args = args.scheduler_args
        self.scheduler_module = args.scheduler_module
        self.scheduler_env = args.scheduler_env
        self.scheduler_analysis_time = args.scheduler_analysis_time

        self.waveform_approximant = args.waveform_approximant

        self.time_reference = args.time_reference
        self.reference_frame = args.reference_frame
        self.likelihood_type = args.likelihood_type
        self.duration = args.duration
        self.prior_file = args.prior_file
        self.prior_dict = args.prior_dict
        self.default_prior = args.default_prior

        self.run_local = args.local
        self.local_generation = args.local_generation
        self.local_plot = args.local_plot

        self.post_trigger_duration = args.post_trigger_duration

        self.ignore_gwpy_data_quality_check = args.ignore_gwpy_data_quality_check
        self.trigger_time = args.trigger_time
        self.deltaT = args.deltaT
        self.gps_tuple = args.gps_tuple
        self.gps_file = args.gps_file
        self.timeslide_file = args.timeslide_file
        self.gaussian_noise = args.gaussian_noise
        self.zero_noise = args.zero_noise
        self.n_simulation = args.n_simulation

        self.injection = args.injection
        self.injection_numbers = args.injection_numbers
        self.injection_file = args.injection_file
        self.injection_dict = args.injection_dict
        self.injection_waveform_approximant = args.injection_waveform_approximant
        self.generation_seed = args.generation_seed
        if self.injection:
            self.check_injection()

        self.request_memory = args.request_memory
        self.request_memory_generation = args.request_memory_generation
        self.request_cpus = args.request_cpus
        self.sampler_kwargs = args.sampler_kwargs
        self.mpi_samplers = ["pymultinest"]
        self.use_mpi = (self.sampler in self.mpi_samplers) and (self.request_cpus > 1)

        if self.create_plots:
            for plot_attr in [
                "calibration",
                "corner",
                "marginal",
                "skymap",
                "waveform",
                "format",
            ]:
                attr = f"plot_{plot_attr}"
                setattr(self, attr, getattr(args, attr))

        self.postprocessing_executable = args.postprocessing_executable
        self.postprocessing_arguments = args.postprocessing_arguments
        self.single_postprocessing_executable = args.single_postprocessing_executable
        self.single_postprocessing_arguments = args.single_postprocessing_arguments

        self.summarypages_arguments = args.summarypages_arguments

        self.check_source_model(args)

        self.extra_lines = []
        self.requirements = []

    @property
    def ini(self):
        return self._ini

    @ini.setter
    def ini(self, ini):
        if os.path.isfile(ini) is False:
            raise FileNotFoundError(f"No ini file {ini} found")
        self._ini = os.path.relpath(ini)

    @property
    def notification(self):
        return self._notification

    @notification.setter
    def notification(self, notification):
        valid_settings = ["Always", "Complete", "Error", "Never"]
        if notification in valid_settings:
            self._notification = notification
        else:
            raise BilbyPipeError(
                "'{}' is not a valid notification setting. "
                "Valid settings are {}.".format(notification, valid_settings)
            )

    @property
    def initialdir(self):
        return os.getcwd()

    @property
    def gps_file(self):
        return self._gps_file

    @gps_file.setter
    def gps_file(self, gps_file):
        self._gps_file = gps_file
        if self.gps_file is not None:
            self._parse_gps_file()

    @property
    def n_simulation(self):
        return self._n_simulation

    @n_simulation.setter
    def n_simulation(self, n_simulation):
        logger.info(f"Setting n_simulation={n_simulation}")
        if isinstance(n_simulation, int) and n_simulation >= 0:
            self._n_simulation = n_simulation
        elif n_simulation is None:
            self._n_simulation = 0
        else:
            raise BilbyPipeError(f"Input n_simulation={n_simulation} not understood")

    @property
    def request_memory(self):
        return self._request_memory

    @request_memory.setter
    def request_memory(self, request_memory):
        logger.info(f"Setting analysis request_memory={request_memory}GB")
        self._request_memory = f"{request_memory} GB"

    @property
    def request_memory_generation(self):
        return self._request_memory_generation

    @request_memory_generation.setter
    def request_memory_generation(self, request_memory_generation):
        if request_memory_generation is None:
            roq = "roq" in self.likelihood_type.lower()
            request_memory_generation = request_memory_generation_lookup(
                self.duration, roq=roq
            )
        logger.info(f"Setting request_memory_generation={request_memory_generation}GB")
        self._request_memory_generation = f"{request_memory_generation} GB"

    @property
    def request_cpus(self):
        return self._request_cpus

    @request_cpus.setter
    def request_cpus(self, request_cpus):
        logger.info(f"Setting analysis request_cpus = {request_cpus}")
        self._request_cpus = request_cpus

    @property
    def use_mpi(self):
        return self._use_mpi

    @use_mpi.setter
    def use_mpi(self, use_mpi):
        if use_mpi:
            logger.info(f"Turning on MPI for {self.sampler}")
        self._use_mpi = use_mpi

    @staticmethod
    def check_source_model(args):
        """ Check the source model consistency with the approximant """
        if "tidal" in args.waveform_approximant.lower():
            if "neutron_star" not in args.frequency_domain_source_model.lower():
                msg = [
                    tcolors.WARNING,
                    "You appear to be using a tidal waveform with the",
                    f"{args.frequency_domain_source_model} source model.",
                    "You may want to use `frequency-domain-source-model=",
                    "lal_binary_neutron_star`.",
                    tcolors.END,
                ]
                logger.warning(" ".join(msg))

    def check_injection(self):
        """Check injection behaviour

        If injections are requested, either use the injection-dict,
        injection-file, or create an injection-file

        """
        default_injection_file_name = "{}/{}_injection_file.dat".format(
            self.data_directory, self.label
        )
        if self.injection_dict is not None:
            logger.info(
                "Using injection dict from ini file {}".format(
                    json.dumps(self.injection_dict, indent=2)
                )
            )
        elif self.injection_file is not None:
            logger.info(f"Using injection file {self.injection_file}")
        elif os.path.isfile(default_injection_file_name):
            # This is done to avoid overwriting the injection file
            logger.info(f"Using injection file {default_injection_file_name}")
            self.injection_file = default_injection_file_name
        else:
            logger.info("No injection file found, generating one now")
            if self.gps_file is not None:
                if self.n_simulation > 0 and self.n_simulation != len(self.gpstimes):
                    raise BilbyPipeError(
                        "gps_file option and n_simulation options not yet implemented"
                    )
                n_injection = len(self.gpstimes)
            else:
                n_injection = self.n_simulation
            if self.trigger_time is None:
                trigger_time_injections = 0
            else:
                trigger_time_injections = self.trigger_time
            create_injection_file(
                filename=default_injection_file_name,
                prior_file=self.prior_file,
                prior_dict=self.prior_dict,
                n_injection=n_injection,
                trigger_time=trigger_time_injections,
                deltaT=self.deltaT,
                gps_file=self.gps_file,
                duration=self.duration,
                post_trigger_duration=self.post_trigger_duration,
                generation_seed=self.generation_seed,
                extension="dat",
                default_prior=self.default_prior,
            )
            self.injection_file = default_injection_file_name

        # Check the gps_file has the sample length as number of simulation
        if self.gps_file is not None:
            if len(self.gpstimes) != len(self.injection_df):
                raise BilbyPipeError("Injection file length does not match gps_file")

        if self.n_simulation > 0:
            if self.n_simulation != len(self.injection_df):
                raise BilbyPipeError(
                    "n-simulation does not match the number of injections: "
                    "please check your ini file"
                )
        elif self.n_simulation == 0 and self.gps_file is None:
            self.n_simulation = len(self.injection_df)
            logger.info(f"Setting n_simulation={self.n_simulation} to match injections")


def write_complete_config_file(parser, args, inputs):
    args_dict = vars(args).copy()
    for key, val in args_dict.items():
        if key == "label":
            continue
        if isinstance(val, str):
            if os.path.isfile(val) or os.path.isdir(val):
                setattr(args, key, os.path.abspath(val))
        if isinstance(val, list):
            if isinstance(val[0], str):
                setattr(args, key, f"[{', '.join(val)}]")
    args.sampler_kwargs = str(inputs.sampler_kwargs)
    parser.write_to_file(
        filename=inputs.complete_ini_file,
        args=args,
        overwrite=False,
        include_description=False,
    )

    # Verify that the written complete config is identical to the source config
    complete_args = parser.parse([inputs.complete_ini_file])
    complete_inputs = MainInput(complete_args, "")
    ignore_keys = ["scheduler_module"]
    differences = []
    for key, val in inputs.__dict__.items():
        if key in ignore_keys:
            continue
        if key not in complete_args:
            continue
        if isinstance(val, pd.DataFrame) and all(val == complete_inputs.__dict__[key]):
            continue
        if isinstance(val, np.ndarray) and all(
            np.array(val) == np.array(complete_inputs.__dict__[key])
        ):
            continue
        if isinstance(val, str) and os.path.isfile(val):
            # Check if it is relpath vs abspath
            if os.path.abspath(val) == os.path.abspath(complete_inputs.__dict__[key]):
                continue
        if val == complete_inputs.__dict__[key]:
            continue

        differences.append(key)

    if len(differences) > 0:
        for key in differences:
            print(key, f"{inputs.__dict__[key]} -> {complete_inputs.__dict__[key]}")
        raise BilbyPipeError(
            "The written config file {} differs from the source {} in {}".format(
                inputs.ini, inputs.complete_ini_file, differences
            )
        )


def perform_runtime_checks(inputs, args):
    """ Perform a set of run-time checks """
    inputs.sampler = args.sampler


def main():
    """ Top-level interface for bilby_pipe """
    parser = create_parser(top_level=True)
    args, unknown_args = parse_args(get_command_line_arguments(), parser)

    # Check and sort outdir
    args.outdir = args.outdir.replace("'", "").replace('"', "")
    if args.overwrite_outdir is False:
        args.outdir = get_outdir_name(args.outdir)

    log_version_information()
    inputs = MainInput(args, unknown_args)
    perform_runtime_checks(inputs, args)
    inputs.pretty_print_prior()
    write_complete_config_file(parser, args, inputs)
    generate_dag(inputs)

    if len(unknown_args) > 0:
        msg = [tcolors.WARNING, f"Unrecognized arguments {unknown_args}", tcolors.END]
        logger.warning(" ".join(msg))
