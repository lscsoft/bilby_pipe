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
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pycondor

from . import slurm
from .create_injections import create_injection_file
from .input import Input
from .overview import create_overview
from .parser import create_parser
from .utils import (
    ArgumentsString,
    BilbyPipeError,
    DataDump,
    convert_string_to_tuple,
    get_command_line_arguments,
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
        logger.debug("Command line arguments: {}".format(args))

        self.known_args = args
        self.unknown_args = unknown_args
        self.ini = args.ini
        self.submit = args.submit
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

        self.webdir = args.webdir
        self.email = args.email
        self.existing_dir = args.existing_dir

        self.scheduler = args.scheduler
        self.scheduler_args = args.scheduler_args
        self.scheduler_module = args.scheduler_module
        self.scheduler_env = args.scheduler_env

        self.waveform_approximant = args.waveform_approximant
        self.catch_waveform_errors = args.catch_waveform_errors
        self.pn_spin_order = args.pn_spin_order
        self.pn_tidal_order = args.pn_tidal_order
        self.pn_phase_order = args.pn_phase_order
        self.pn_amplitude_order = args.pn_amplitude_order

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

        if self.create_plots:
            for plot_attr in [
                "calibration",
                "corner",
                "marginal",
                "skymap",
                "waveform",
                "format",
            ]:
                attr = "plot_{}".format(plot_attr)
                setattr(self, attr, getattr(args, attr))

        self.postprocessing_executable = args.postprocessing_executable
        self.postprocessing_arguments = args.postprocessing_arguments

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
            raise FileNotFoundError("No ini file {} found".format(ini))
        self._ini = os.path.relpath(ini)

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
        logger.info("Setting n_simulation={}".format(n_simulation))
        if isinstance(n_simulation, int) and n_simulation >= 0:
            self._n_simulation = n_simulation
        elif n_simulation is None:
            self._n_simulation = 0
        else:
            raise BilbyPipeError(
                "Input n_simulation={} not understood".format(n_simulation)
            )

    @property
    def request_memory(self):
        return self._request_memory

    @request_memory.setter
    def request_memory(self, request_memory):
        logger.info("Setting analysis request_memory={}GB".format(request_memory))
        self._request_memory = "{} GB".format(request_memory)

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
        logger.info(
            "Setting request_memory_generation={}GB".format(request_memory_generation)
        )
        self._request_memory_generation = "{} GB".format(request_memory_generation)

    @property
    def request_cpus(self):
        return self._request_cpus

    @request_cpus.setter
    def request_cpus(self, request_cpus):
        logger.info("Setting analysis request_cpus = {}".format(request_cpus))
        self._request_cpus = request_cpus

    @staticmethod
    def check_source_model(args):
        """ Check the source model consistency with the approximant """
        if "tidal" in args.waveform_approximant.lower():
            if "neutron_star" not in args.frequency_domain_source_model.lower():
                msg = [
                    tcolors.WARNING,
                    "You appear to be using a tidal waveform with the",
                    "{} source model.".format(args.frequency_domain_source_model),
                    "You may want to use `frequency-domain-source-model=",
                    "lal_binary_neutron_star`.",
                    tcolors.END,
                ]
                logger.warning(" ".join(msg))

    def check_injection(self):
        """ Check injection behaviour

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
            logger.info("Using injection file {}".format(self.injection_file))
        elif os.path.isfile(default_injection_file_name):
            # This is done to avoid overwriting the injection file
            logger.info("Using injection file {}".format(default_injection_file_name))
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
            logger.info(
                "Setting n_simulation={} to match injections".format(self.n_simulation)
            )


class Dag(object):
    """ Base Dag object, handles the creation of the DAG structure """

    def __init__(self, inputs):
        self.inputs = inputs
        self.dag_name = "dag_{}".format(inputs.label)

        # The slurm setup uses the pycondor dag as a base
        if self.inputs.scheduler.lower() in ["condor", "slurm"]:
            self.setup_pycondor_dag()

    def setup_pycondor_dag(self):
        self.pycondor_dag = pycondor.Dagman(
            name=self.dag_name, submit=self.inputs.submit_directory
        )

    def build(self):
        if self.inputs.scheduler.lower() == "condor":
            self.build_pycondor_dag()
            self.write_bash_script()
        elif self.inputs.scheduler.lower() == "slurm":
            self.scheduler = self.inputs.scheduler
            self.scheduler_args = self.inputs.scheduler_args
            self.scheduler_module = self.inputs.scheduler_module
            self.scheduler_env = self.inputs.scheduler_env
            self.build_slurm_submit()

    def build_pycondor_dag(self):
        """ Build the pycondor dag, optionally submit them if requested """
        submitted = False
        if self.inputs.submit:
            try:
                self.pycondor_dag.build_submit(fancyname=False)
                submitted = True
            except OSError:
                logger.warning("Unable to submit files")
                self.pycondor_dag.build(fancyname=False)
        else:
            self.pycondor_dag.build(fancyname=False)

        if submitted:
            logger.info("DAG generation complete and submitted")
        else:
            command_line = "$ condor_submit_dag {}".format(
                os.path.relpath(self.pycondor_dag.submit_file)
            )
            logger.info(
                "DAG generation complete, to submit jobs run:\n  {}".format(
                    command_line
                )
            )

        # Debugging feature: create a "visualisation" of the DAG
        if "--create-dag-plot" in sys.argv:
            try:
                self.pycondor_dag.visualize(
                    "{}/{}_visualization.png".format(
                        self.inputs.submit_directory, self.pycondor_dag.name
                    )
                )
            except Exception:
                pass

    def build_slurm_submit(self):
        """ Build slurm submission scripts """

        slurm.SubmitSLURM(self)

    def write_bash_script(self):
        """ Write the dag to a bash script for command line running """
        with open(self.bash_file, "w") as ff:
            ff.write("#!/usr/bin/env bash\n\n")
            for node in self.pycondor_dag.nodes:
                ff.write("# {}\n".format(node.name))
                ff.write(
                    "# PARENTS {}\n".format(
                        " ".join([job.name for job in node.parents])
                    )
                )
                ff.write(
                    "# CHILDREN {}\n".format(
                        " ".join([job.name for job in node.children])
                    )
                )
                job_str = "{} {}\n\n".format(node.executable, node.args[0].arg)
                ff.write(job_str)

    @property
    def bash_file(self):
        bash_file = self.pycondor_dag.submit_file.replace(".submit", ".sh").replace(
            "dag_", "bash_"
        )
        return bash_file


def _log_output_error_submit_lines(logdir, prefix):
    """Returns the filepaths for condor log, output, and error options

    Parameters
    ----------
    logdir : str
        the target directory for the files
    prefix : str
        the prefix for the files

    Returns
    -------
    log, output, error : list of str
        the list of three file paths to be passed to pycondor.Job

    Examples
    --------
    >>> Dag._log_output_error_submit_lines("test", "job")
    ['log = test/job.log',
     'output = test/job.out',
     'error = test/job.err']
    """
    logpath = Path(logdir)
    filename = "{}.{{}}".format(prefix)
    return [
        "{} = {}".format(opt, str(logpath / filename.format(opt[:3])))
        for opt in ("log", "output", "error")
    ]


class Node(object):
    """ Base Node object, handles creation of arguments, executables, etc """

    def __init__(self, inputs):
        self.inputs = inputs
        self._universe = "vanilla"
        self.request_disk = None
        self.online_pe = self.inputs.online_pe
        self.getenv = True
        self.notification = False
        self.retry = None
        self.verbose = 0
        self.extra_lines = list(self.inputs.extra_lines)
        self.requirements = (
            [self.inputs.requirements] if self.inputs.requirements else []
        )

    @property
    def universe(self):
        return self._universe

    def process_node(self):
        self.create_pycondor_job()

        if self.inputs.run_local:
            logger.info(
                "Running command: "
                + " ".join([self.executable] + self.arguments.argument_list)
            )
            subprocess.run([self.executable] + self.arguments.argument_list, check=True)

    @staticmethod
    def _get_executable_path(exe_name):
        exe = shutil.which(exe_name)
        if exe is not None:
            return exe
        else:
            raise OSError(
                "{} not installed on this system, unable to proceed".format(exe_name)
            )

    def setup_arguments(
        self, add_command_line_args=True, add_ini=True, add_unknown_args=True
    ):
        self.arguments = ArgumentsString()
        if add_ini:
            self.arguments.add_positional_argument(self.inputs.complete_ini_file)
        if add_unknown_args:
            self.arguments.add_unknown_args(self.inputs.unknown_args)
        if add_command_line_args:
            self.arguments.add_command_line_arguments()

    @property
    def log_directory(self):
        raise NotImplementedError()

    def create_pycondor_job(self):
        job_name = self.job_name
        self.extra_lines.extend(
            _log_output_error_submit_lines(self.log_directory, job_name)
        )
        self.extra_lines.append("accounting_group = {}".format(self.inputs.accounting))

        if self.online_pe:
            self.extra_lines.append("+Online_CBC_PE_Daily = True")
            self.requirements.append("((TARGET.Online_CBC_PE_Daily =?= True))")

        if self.universe != "local" and self.inputs.osg:
            _osg_lines, _osg_reqs = self._osg_submit_options(
                self.executable, has_ligo_frames=True
            )
            self.extra_lines.extend(_osg_lines)
            self.requirements.append(_osg_reqs)

        self.job = pycondor.Job(
            name=job_name,
            executable=self.executable,
            submit=self.inputs.submit_directory,
            request_memory=self.request_memory,
            request_disk=self.request_disk,
            request_cpus=1,
            getenv=self.getenv,
            universe=self.universe,
            initialdir=self.inputs.initialdir,
            notification=self.notification,
            requirements=" && ".join(self.requirements),
            extra_lines=self.extra_lines,
            dag=self.dag.pycondor_dag,
            arguments=self.arguments.print(),
            retry=self.retry,
            verbose=self.verbose,
        )
        logger.debug("Adding job: {}".format(job_name))

    @staticmethod
    def _checkpoint_submit_lines(code=130):
        return [
            # needed for htcondor < 8.9.x (probably)
            "+CheckpointExitBySignal = False",
            "+CheckpointExitCode = {}".format(code),
            # htcondor >= 8.9.x (probably)
            "+SuccessCheckpointExitBySignal = False",
            "+SuccessCheckpointExitCode = {}".format(code),
            # ask condor to provide the checkpoint signals
            "+WantCheckpointSignal = True",
            '+CheckpointSig = "SIGTERM"',
        ]

    @staticmethod
    def _condor_file_transfer_lines(inputs, outputs):
        return [
            "should_transfer_files = YES",
            "transfer_input_files = {}".format(",".join(inputs)),
            "transfer_output_files = {}".format(",".join(outputs)),
            "when_to_transfer_output = ON_EXIT_OR_EVICT",
            "stream_error = True",
            "stream_output = True",
        ]

    @staticmethod
    def _relative_topdir(path, reference):
        """Returns the top-level directory name of a path relative
        to a reference
        """
        try:
            return str(Path(path).resolve().relative_to(reference))
        except ValueError as exc:
            exc.args = ("cannot format {} relative to {}".format(path, reference),)
            raise

    def _osg_submit_options(self, executable, has_ligo_frames=False):
        """Returns the extra submit lines and requirements to enable running
        a job on the Open Science Grid

        Returns
        -------
        lines : list
            the list of extra submit lines to include
        requirements : str
            the extra requirements line to include
        """
        # required for OSG submission
        lines = ["+OpenScienceGrid = True"]
        requirements = ["(IS_GLIDEIN=?=True)"]

        # if we need GWF data:
        if has_ligo_frames:
            requirements.append("(HAS_LIGO_FRAMES=?=True)")

        # if need a /cvmfs repo for the software:
        # NOTE: this should really be applied to _all_ workflows
        #       that need CVMFS, not just distributed ones, but
        #       not all local pools advertise the CVMFS repo flags
        if executable.startswith("/cvmfs"):
            repo = executable.split(os.path.sep, 3)[2]
            requirements.append(
                "(HAS_CVMFS_{}=?=True)".format(re.sub("[.-]", "_", repo))
            )

        return lines, " && ".join(requirements)


class GenerationNode(Node):
    def __init__(self, inputs, trigger_time, idx, dag):
        super().__init__(inputs)
        self.inputs = inputs
        self.trigger_time = trigger_time
        self.idx = idx
        self.dag = dag

        self.setup_arguments()
        self.arguments.add("label", self.label)
        self.arguments.add("idx", self.idx)
        self.arguments.add("trigger-time", self.trigger_time)
        if self.inputs.injection_file is not None:
            self.arguments.add("injection-file", self.inputs.injection_file)
        if self.inputs.timeslide_file is not None:
            self.arguments.add("timeslide-file", self.inputs.timeslide_file)
        self.process_node()

    @property
    def executable(self):
        return self._get_executable_path("bilby_pipe_generation")

    @property
    def request_memory(self):
        return self.inputs.request_memory_generation

    @property
    def log_directory(self):
        return self.inputs.data_generation_log_directory

    @property
    def universe(self):
        if self.inputs.local_generation:
            logger.debug(
                "Data generation done locally: please do not use this when "
                "submitting a large number of jobs"
            )
            universe = "local"
        else:
            logger.debug(
                "All data will be grabbed in the {} universe".format(self._universe)
            )
            universe = self._universe
        return universe

    @property
    def job_name(self):
        job_name = "{}_data{}_{}_generation".format(
            self.inputs.label, str(self.idx), self.trigger_time
        )
        job_name = job_name.replace(".", "-")
        return job_name

    @property
    def label(self):
        return self.job_name

    @property
    def data_dump_file(self):
        return DataDump.get_filename(self.inputs.data_directory, self.label)


class AnalysisNode(Node):
    def __init__(self, inputs, generation_node, detectors, sampler, parallel_idx, dag):
        super().__init__(inputs)
        self.dag = dag
        self.generation_node = generation_node
        self.detectors = detectors
        self.parallel_idx = parallel_idx

        data_label = generation_node.job_name
        base_name = data_label.replace("generation", "analysis")
        self.base_job_name = "{}_{}_{}".format(base_name, "".join(detectors), sampler)
        if parallel_idx != "":
            self.job_name = "{}_{}".format(self.base_job_name, parallel_idx)
        else:
            self.job_name = self.base_job_name
        self.label = self.job_name

        self.setup_arguments()

        if self.inputs.transfer_files or self.inputs.osg:
            data_dump_file = generation_node.data_dump_file
            input_files_to_transfer = [
                str(data_dump_file),
                str(self.inputs.complete_ini_file),
            ]
            self.extra_lines.extend(
                self._condor_file_transfer_lines(
                    input_files_to_transfer,
                    [self._relative_topdir(self.inputs.outdir, self.inputs.initialdir)],
                )
            )
            self.arguments.add("outdir", os.path.basename(self.inputs.outdir))

        for det in detectors:
            self.arguments.add("detectors", det)
        self.arguments.add("label", self.label)
        self.arguments.add("data-dump-file", generation_node.data_dump_file)
        self.arguments.add("sampler", sampler)

        self.extra_lines.extend(self._checkpoint_submit_lines())

        self.process_node()
        self.job.add_parent(generation_node.job)

    @property
    def executable(self):
        return self._get_executable_path("bilby_pipe_analysis")

    @property
    def request_memory(self):
        return self.inputs.request_memory

    @property
    def log_directory(self):
        return self.inputs.data_analysis_log_directory

    @property
    def result_file(self):
        return "{}/{}_result.json".format(self.inputs.result_directory, self.job_name)


class MergeNode(Node):
    def __init__(self, inputs, parallel_node_list, detectors, dag):
        super().__init__(inputs)
        self.dag = dag

        self.job_name = "{}_merge".format(parallel_node_list[0].base_job_name)
        self.label = "{}_merge".format(parallel_node_list[0].base_job_name)
        self.setup_arguments(
            add_ini=False, add_unknown_args=False, add_command_line_args=False
        )
        self.arguments.append("--result")
        for pn in parallel_node_list:
            self.arguments.append(pn.result_file)
        self.arguments.add("outdir", self.inputs.result_directory)
        self.arguments.add("label", self.label)
        self.arguments.add_flag("merge")

        self.process_node()
        for pn in parallel_node_list:
            self.job.add_parent(pn.job)

    @property
    def executable(self):
        return self._get_executable_path("bilby_result")

    @property
    def request_memory(self):
        return "16 GB"

    @property
    def log_directory(self):
        return self.inputs.data_analysis_log_directory

    @property
    def result_file(self):
        return "{}/{}_result.json".format(self.inputs.result_directory, self.label)


class PlotNode(Node):
    def __init__(self, inputs, merged_node, dag):
        super().__init__(inputs)
        self.dag = dag
        self.job_name = merged_node.job_name + "_plot"
        self.label = merged_node.job_name + "_plot"
        self.setup_arguments(
            add_ini=False, add_unknown_args=False, add_command_line_args=False
        )
        self.arguments.add("result", merged_node.result_file)
        self.arguments.add("outdir", self.inputs.result_directory)
        for plot_type in ["calibration", "corner", "marginal", "skymap", "waveform"]:
            if getattr(inputs, "plot_{}".format(plot_type), False):
                self.arguments.add_flag(plot_type)
        self.arguments.add("format", inputs.plot_format)
        self.process_node()
        self.job.add_parent(merged_node.job)

    @property
    def executable(self):
        return self._get_executable_path("bilby_pipe_plot")

    @property
    def request_memory(self):
        return "32 GB"

    @property
    def log_directory(self):
        return self.inputs.data_analysis_log_directory

    @property
    def universe(self):
        if self.inputs.local_plot:
            logger.debug(
                "Data plotting done locally: please do not use this when "
                "submitting a large number of jobs"
            )
            universe = "local"
        else:
            logger.debug(
                "All data will be grabbed in the {} universe".format(self._universe)
            )
            universe = self._universe
        return universe


class PESummaryNode(Node):
    def __init__(self, inputs, merged_node_list, generation_node_list, dag):
        super().__init__(inputs)
        self.dag = dag
        self.job_name = "{}_pesummary".format(inputs.label)

        n_results = len(merged_node_list)
        result_files = [merged_node.result_file for merged_node in merged_node_list]
        labels = [merged_node.label for merged_node in merged_node_list]

        self.setup_arguments(
            add_ini=False, add_unknown_args=False, add_command_line_args=False
        )
        self.arguments.add("webdir", self.inputs.webdir)
        if self.inputs.email is not None:
            self.arguments.add("email", self.inputs.email)
        self.arguments.add("config", " ".join([self.inputs.ini] * n_results))
        self.arguments.add("samples", "{}".format(" ".join(result_files)))

        # Using append here as summary pages doesn't take a full name for approximant
        self.arguments.append("-a")
        self.arguments.append(" ".join([self.inputs.waveform_approximant] * n_results))

        if len(generation_node_list) == 1:
            self.arguments.add("gwdata", generation_node_list[0].data_dump_file)
        elif len(generation_node_list) > 1:
            logger.info(
                "Not adding --gwdata to PESummary job as there are multiple files"
            )
        existing_dir = self.inputs.existing_dir
        if existing_dir is not None:
            self.arguments.add("existing_webdir", existing_dir)

        if isinstance(self.inputs.summarypages_arguments, dict):
            if "labels" not in self.inputs.summarypages_arguments.keys():
                self.arguments.append("--labels {}".format(" ".join(labels)))
            else:
                if len(labels) != len(result_files):
                    raise BilbyPipeError(
                        "Please provide the same number of labels for postprocessing "
                        "as result files"
                    )
            not_recognised_arguments = {}
            for key, val in self.inputs.summarypages_arguments.items():
                if key == "nsamples_for_skymap":
                    self.arguments.add("nsamples_for_skymap", val)
                elif key == "gw":
                    self.arguments.add_flag("gw")
                elif key == "no_ligo_skymap":
                    self.arguments.add_flag("no_ligo_skymap")
                elif key == "burnin":
                    self.arguments.add("burnin", val)
                elif key == "kde_plot":
                    self.arguments.add_flag("kde_plot")
                elif key == "gracedb":
                    self.arguments.add("gracedb", val)
                elif key == "palette":
                    self.arguments.add("palette", val)
                elif key == "include_prior":
                    self.arguments.add_flag("include_prior")
                elif key == "notes":
                    self.arguments.add("notes", val)
                elif key == "publication":
                    self.arguments.add_flag("publication")
                elif key == "labels":
                    self.arguments.add("labels", "{}".format(" ".join(val)))
                else:
                    not_recognised_arguments[key] = val
            if not_recognised_arguments != {}:
                logger.warn(
                    "Did not recognise the summarypages_arguments {}. To find "
                    "the full list of available arguments, please run "
                    "summarypages --help".format(not_recognised_arguments)
                )

        self.process_node()
        for merged_node in merged_node_list:
            self.job.add_parent(merged_node.job)

    @property
    def executable(self):
        return self._get_executable_path("summarypages")

    @property
    def request_memory(self):
        return "16 GB"

    @property
    def log_directory(self):
        return self.inputs.summary_log_directory


class PostProcessAllResultsNode(Node):
    def __init__(self, inputs, merged_node_list, dag):
        super().__init__(inputs)
        self.dag = dag
        self.job_name = "{}_postprocess_all".format(self.inputs.label)
        self.setup_arguments(
            add_ini=False, add_unknown_args=False, add_command_line_args=False
        )
        self.arguments.argument_list = self.inputs.postprocessing_arguments
        self.process_node()
        for node in merged_node_list:
            self.job.add_parent(node.job)

    @property
    def executable(self):
        return self._get_executable_path(self.inputs.postprocessing_executable)

    @property
    def request_memory(self):
        return "32 GB"

    @property
    def log_directory(self):
        return self.inputs.data_analysis_log_directory


def get_trigger_time_list(inputs):
    """ Returns a list of GPS trigger times for each data segment """
    if inputs.gaussian_noise:
        trigger_times = [0] * inputs.n_simulation
    elif inputs.trigger_time is not None:
        trigger_times = [inputs.trigger_time]
    elif inputs.gps_tuple is not None:
        start, dt, N = convert_string_to_tuple(inputs.gps_tuple)
        start_times = np.linspace(start, start + (N - 1) * dt, N)
        trigger_times = start_times + inputs.duration - inputs.post_trigger_duration
    elif inputs.gps_file is not None:
        start_times = inputs.gpstimes
        trigger_times = start_times + inputs.duration - inputs.post_trigger_duration
    else:
        raise BilbyPipeError("Unable to determine input trigger times from ini file")
    logger.info("Setting segment trigger-times {}".format(trigger_times))
    return trigger_times


def get_detectors_list(inputs):
    detectors_list = []
    detectors_list.append(inputs.detectors)
    if inputs.coherence_test:
        for detector in inputs.detectors:
            detectors_list.append([detector])
    return detectors_list


def get_parallel_list(inputs):
    if inputs.n_parallel == 1:
        return [""]
    else:
        return ["par{}".format(idx) for idx in range(inputs.n_parallel)]


def generate_dag(inputs):
    dag = Dag(inputs)
    trigger_times = get_trigger_time_list(inputs)

    generation_node_list = []
    for idx, trigger_time in enumerate(trigger_times):
        generation_node = GenerationNode(
            inputs, trigger_time=trigger_time, idx=idx, dag=dag
        )
        generation_node_list.append(generation_node)

    detectors_list = get_detectors_list(inputs)
    parallel_list = get_parallel_list(inputs)
    merged_node_list = []
    all_parallel_node_list = []
    for generation_node in generation_node_list:
        for detectors in detectors_list:
            parallel_node_list = []
            for parallel_idx in parallel_list:
                analysis_node = AnalysisNode(
                    inputs,
                    generation_node=generation_node,
                    detectors=detectors,
                    parallel_idx=parallel_idx,
                    dag=dag,
                    sampler=inputs.sampler,
                )
                parallel_node_list.append(analysis_node)
                all_parallel_node_list.append(analysis_node)

            if len(parallel_node_list) == 1:
                merged_node_list.append(analysis_node)
            else:
                merge_node = MergeNode(
                    inputs=inputs,
                    parallel_node_list=parallel_node_list,
                    detectors=detectors,
                    dag=dag,
                )
                merged_node_list.append(merge_node)

    plot_nodes_list = []
    for merged_node in merged_node_list:
        if inputs.create_plots:
            plot_nodes_list.append(PlotNode(inputs, merged_node, dag=dag))

    if inputs.create_summary:
        PESummaryNode(inputs, merged_node_list, generation_node_list, dag=dag)
    if inputs.postprocessing_executable is not None:
        PostProcessAllResultsNode(inputs, merged_node_list, dag)

    dag.build()
    create_overview(
        inputs,
        generation_node_list,
        all_parallel_node_list,
        merged_node_list,
        plot_nodes_list,
    )


def write_complete_config_file(parser, args, inputs):
    args_dict = vars(args).copy()
    for key, val in args_dict.items():
        if isinstance(val, str):
            if os.path.isfile(val) or os.path.isdir(val):
                setattr(args, key, os.path.abspath(val))
        if isinstance(val, list):
            if isinstance(val[0], str):
                setattr(args, key, "[{}]".format(", ".join(val)))
    parser.write_to_file(
        filename=inputs.complete_ini_file,
        args=args,
        overwrite=False,
        include_description=False,
    )

    # Verify that the written complete config is identical to the source config
    complete_args = parser.parse([inputs.complete_ini_file])
    complete_inputs = MainInput(complete_args, "")
    ignore_keys = ["known_args", "unknown_args", "_ini", "_webdir", "_prior_dict"]
    differences = []
    for key, val in inputs.__dict__.items():
        if key in ignore_keys:
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
            print(
                key,
                "{} -- {}".format(inputs.__dict__[key], complete_inputs.__dict__[key]),
            )
        raise BilbyPipeError(
            "The written config file {} differs from the source {} in {}".format(
                inputs.ini, inputs.complete_ini_file, differences
            )
        )


def main():
    """ Top-level interface for bilby_pipe """
    parser = create_parser(top_level=True)
    args, unknown_args = parse_args(get_command_line_arguments(), parser)
    log_version_information()
    inputs = MainInput(args, unknown_args)
    write_complete_config_file(parser, args, inputs)
    generate_dag(inputs)

    if len(unknown_args) > 1:
        msg = [
            tcolors.WARNING,
            "Unrecognized arguments {}".format(unknown_args),
            tcolors.END,
        ]
        logger.warning(" ".join(msg))
