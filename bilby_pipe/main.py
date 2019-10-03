#!/usr/bin/env python
"""
bilby_pipe is a command line tools for taking user input (as command line
arguments or an ini file) and creating DAG files for submitting bilby parameter
estimation jobs.
"""
import itertools
from collections import namedtuple
import os
import shutil
import sys
import subprocess
from pathlib import Path

import pycondor

from .utils import (
    logger,
    parse_args,
    BilbyPipeError,
    DataDump,
    ArgumentsString,
    get_command_line_arguments,
    request_memory_generation_lookup,
    tcolors,
    log_version_information,
)
from . import create_injections
from . import slurm
from .input import Input
from .parser import create_parser

JobInput = namedtuple("level_A_job_input", "idx meta_label kwargs")


class MainInput(Input):
    """ An object to hold all the inputs to bilby_pipe

    Parameters
    ----------
    parser: BilbyArgParser, optional
        The parser containing the command line / ini file inputs
    args_list: list, optional
        A list of the arguments to parse. Defaults to `sys.argv[1:]`

    Attributes
    ----------
    ini: str
        The path to the ini file
    submit: bool
        If true, user-input to also submit the jobs
    label: str
        A label describing the job
    outdir: str
        The path to the directory where output will be stored
    create_summary: bool
        If true, create a summary page
    accounting: str
        The accounting group to use
    coherence_test: bool
        If true, run the coherence test
    detectors: list
        A list of the detectors to include, e.g., ['H1', 'L1']
    unknown_args: list
        A list of unknown command line arguments

    """

    def __init__(self, args, unknown_args):
        logger.debug("Creating new Input object")
        logger.debug("Command line arguments: {}".format(args))

        self.unknown_args = unknown_args
        self.ini = args.ini
        self.submit = args.submit
        self.create_plots = args.create_plots
        self.singularity_image = args.singularity_image
        self.outdir = args.outdir
        self.label = args.label
        self.create_summary = args.create_summary
        self.accounting = args.accounting
        self.sampler = args.sampler
        self.detectors = args.detectors
        self.coherence_test = args.coherence_test
        self.n_parallel = args.n_parallel
        self.transfer_files = args.transfer_files
        self.osg = args.osg

        self.scheduler = args.scheduler
        self.scheduler_args = args.scheduler_args
        self.scheduler_module = args.scheduler_module
        self.scheduler_env = args.scheduler_env

        self.waveform_approximant = args.waveform_approximant
        self.likelihood_type = args.likelihood_type
        self.duration = args.duration
        self.prior_file = args.prior_file

        self.webdir = args.webdir
        self.email = args.email
        self.existing_dir = args.existing_dir

        self.run_local = args.local
        self.local_generation = args.local_generation
        self.local_plot = args.local_plot

        self.gps_file = args.gps_file
        self.trigger_time = args.trigger_time
        self.injection = args.injection
        self.injection_file = args.injection_file
        self.n_injection = args.n_injection

        self.request_memory = args.request_memory
        self.request_memory_generation = args.request_memory_generation
        self.request_cpus = args.request_cpus

        self.postprocessing_executable = args.postprocessing_executable
        self.postprocessing_arguments = args.postprocessing_arguments

        self.check_source_model(args)

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
    def singularity_image(self):
        return self._singularity_image

    @singularity_image.setter
    def singularity_image(self, singularity_image):
        if singularity_image is None:
            self._singularity_image = None
            self.use_singularity = False
        elif isinstance(singularity_image, str):
            self._verify_singularity(singularity_image)
            self._singularity_image = os.path.abspath(singularity_image)
            self.use_singularity = True
        else:
            raise BilbyPipeError("simg={} not understood".format(singularity_image))

    def _verify_singularity(self, singularity_image):
        """ Verify the singularity image exists """
        if os.path.isfile(singularity_image) is False:
            raise FileNotFoundError(
                "singularity_image={} is not a file".format(singularity_image)
            )

    @property
    def use_singularity(self):
        return self._use_singularity

    @use_singularity.setter
    def use_singularity(self, use_singularity):
        if isinstance(use_singularity, bool):
            logger.debug("Setting use_singularity={}".format(use_singularity))
            self._use_singularity = use_singularity
        else:
            raise BilbyPipeError(
                "use_singularity={} not understood".format(use_singularity)
            )

    @property
    def n_level_A_jobs(self):
        return getattr(self, "_n_level_A_jobs", 0)

    @n_level_A_jobs.setter
    def n_level_A_jobs(self, n_level_A_jobs):
        logger.debug("Setting n_level_A_jobs = {}".format(n_level_A_jobs))
        self._n_level_A_jobs = n_level_A_jobs

    @property
    def level_A_labels(self):
        try:
            return self._level_A_jobs
        except AttributeError:
            raise BilbyPipeError("level_A_labels not set")

    @level_A_labels.setter
    def level_A_labels(self, labels):
        self._level_A_jobs = labels

    def _parse_gps_file(self):
        gpstimes = self.read_gps_file()
        n = len(gpstimes)
        logger.info(
            "{} times found in gps_file={}, setting level A jobs".format(
                n, self.gps_file
            )
        )

        self.n_level_A_jobs = n
        self.level_A_labels = [str(x) for x in gpstimes]
        self.gpstimes = gpstimes

    @property
    def n_injection(self):
        return self._n_injection

    @n_injection.setter
    def n_injection(self, n_injection):
        if n_injection is not None:
            self._setup_n_injections(n_injection)
        elif self.injection and hasattr(self, "gpstimes"):
            self._setup_n_injections_from_gpstimes()
        else:
            logger.info("No injections")
            self._n_injection = None

    def _setup_n_injections(self, n_injection):
        self._check_consistency_of_n_injections()
        logger.info("n_injection={}, setting level A jobs".format(n_injection))
        self.n_level_A_jobs = n_injection
        self._n_injection = n_injection
        self.level_A_labels = ["injection{}".format(x) for x in range(n_injection)]

    def _setup_n_injections_from_gpstimes(self):
        logger.info("Injecting signals into segments defined by gpstimes")
        self._n_injection = self.n_level_A_jobs
        self.level_A_labels = [
            label + "_injection{}".format(ii)
            for ii, label in enumerate(self.level_A_labels)
        ]

    def _check_consistency_of_n_injections(self):
        """ If n_injections is given, this checks the consistency with the data setting """
        if hasattr(self, "gpstimes"):
            raise BilbyPipeError("Unable to handle n_injections!=None and gps_file")

        if getattr(self, "trigger_time", None) is not None:
            logger.info("Using trigger_time with n_injections != None")

    @property
    def trigger_time(self):
        return self._trigger_time

    @trigger_time.setter
    def trigger_time(self, trigger_time):
        if trigger_time is not None:
            self._trigger_time = trigger_time
            self.level_A_labels = [str(trigger_time)]
            if self.n_level_A_jobs == 0:
                self.n_level_A_jobs = 1
        else:
            self._trigger_time = None

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
            roq = self.likelihood_type == "ROQGravitationalWaveTransient"
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
                logger.warning(
                    tcolors.WARNING
                    + "You appear to be using a tidal waveform with the "
                    + "{} source model. ".format(args.frequency_domain_source_model)
                    + "You may want to use `frequency-domain-source-model="
                    + "lal_binary_neutron_star`."
                    + tcolors.END
                )


class Dag(object):
    """ A class to handle the creation and building of a DAG

    Parameters
    ----------
    inputs: bilby_pipe.Input
        An object holding the inputs built from the command-line and ini file.

    Other parameters
    ----------------
    request_cpus : int or None, optional
        Number of CPUs to request in submit file.
    getenv : bool or None, optional
        Whether or not to use the current environment settings when running
        the job (default is None).
    universe : str or None, optional
        Universe execution environment to be specified in submit file
        (default is None).
    initialdir : str or None, optional
        Initial directory for relative paths (defaults to the directory was
        the job was submitted from).
    notification : str or None, optional
        E-mail notification preference (default is None).
    requirements : str or None, optional
        Additional requirements to be included in ClassAd.
    extra_lines : list or None, optional
        List of additional lines to be added to submit file.
    dag : Dagman, optional
        If specified, Job will be added to dag (default is None).
    arguments : str or iterable, optional
        Arguments with which to initialize the Job list of arguments
        (default is None).
    retry : int or None, optional
        Option to specify the number of retries for all Job arguments. This
        can be superseded for arguments added via the add_arg() method.
        Note: this feature is only available to Jobs that are submitted via
        a Dagman (default is None; no retries).
    verbose : int, optional
        Level of logging verbosity option are 0-warning, 1-info,
        2-debugging (default is 0).

    Notes
    -----
        The "Other Parameters" are passed directly to
        `pycondor.Job()`. Documentation for these is taken verbatim from the
        API available at https://jrbourbeau.github.io/pycondor/api.html

    """

    def __init__(
        self,
        inputs,
        request_disk=None,
        getenv=True,
        universe="vanilla",
        notification="never",
        requirements=None,
        retry=None,
        verbose=0,
        extra_lines=None,
    ):
        self.request_disk = request_disk
        self.request_cpus = inputs.request_cpus
        self.getenv = getenv
        self.universe = universe
        self.initialdir = inputs.initialdir
        self.notification = notification
        self.requirements = requirements
        self.retry = retry
        self.verbose = verbose
        self.inputs = inputs
        self.extra_lines = list(extra_lines or [])
        if self.inputs.n_level_A_jobs == 0:
            raise BilbyPipeError("ini file contained no data-generation requirement")

        # set submission script
        self.build_submit = inputs.scheduler
        self.scheduler = inputs.scheduler
        if self.scheduler != "condor":
            self.scheduler_args = inputs.scheduler_args
            self.scheduler_module = inputs.scheduler_module
            self.scheduler_env = inputs.scheduler_env

        self.dag_name = "dag_{}".format(inputs.label)
        self.dag = pycondor.Dagman(
            name=self.dag_name, submit=self.inputs.submit_directory
        )

        self.generation_jobs = []
        self.generation_job_labels = []
        self.analysis_jobs = []
        self.analysis_job_labels = []
        self.summary_jobs = []
        self.results_pages = dict()
        if self.inputs.injection:
            self.check_injection()
        self.create_generation_jobs()
        self.create_analysis_jobs()
        self.create_postprocessing_jobs()
        self.create_merge_runs_job()
        if self.inputs.create_plots:
            self.create_plot_jobs()
        if self.inputs.create_summary:
            self.create_summary_jobs()

        self.build_submit()
        if self.inputs.scheduler == "condor":
            self.write_bash_script()

    @property
    def build_submit(self):

        return self._build_submit

    @build_submit.setter
    def build_submit(self, value):
        scheduler_dict = {
            "condor": self.build_condor_dag,
            "slurm": self.build_slurm_submit,
        }

        if value in scheduler_dict.keys():
            self._build_submit = scheduler_dict[value]
        else:
            raise ValueError("Scheduler: {} not implemented ".format(value))

    @staticmethod
    def _get_executable_path(exe_name):
        exe = shutil.which(exe_name)
        if exe is not None:
            return exe
        else:
            raise OSError(
                "{} not installed on this system, unable to proceed".format(exe_name)
            )

    @property
    def generation_executable(self):
        if self.inputs.use_singularity:
            return "/bin/singularity"
        else:
            return self._get_executable_path("bilby_pipe_generation")

    @property
    def analysis_executable(self):
        if self.inputs.use_singularity:
            return "/bin/singularity"
        else:
            return self._get_executable_path("bilby_pipe_analysis")

    @property
    def summary_executable(self):
        return self._get_executable_path("summarypages")

    def check_injection(self):
        """ If injections are requested, create an injection file """
        default_injection_file_name = "{}/{}_injection_file.json".format(
            self.inputs.data_directory, self.inputs.label
        )
        if self.inputs.injection_file is not None:
            logger.info("Using injection file {}".format(self.inputs.injection_file))
        elif os.path.isfile(default_injection_file_name):
            # This is done to avoid overwriting the injection file
            logger.info("Using injection file {}".format(default_injection_file_name))
            self.inputs.injection_file = default_injection_file_name
        else:
            logger.info("No injection file found, generating one now")
            inj_args, inj_unknown_args = parse_args(
                sys.argv[1:], create_injections.create_parser()
            )
            if inj_args.n_injection is None and self.inputs.n_injection is not None:
                inj_args.n_injection = self.inputs.n_injection
            inj_inputs = create_injections.CreateInjectionInput(
                inj_args, inj_unknown_args
            )
            inj_inputs.create_injection_file(default_injection_file_name)
            self.inputs.injection_file = default_injection_file_name
        self.inputs.level_A_labels = [
            "injection{}".format(i)
            for i in range(self.inputs.total_number_of_injections)
        ]

    @property
    def generation_jobs_inputs(self):
        """ A list of dictionaries enumerating all the generation jobs

        This contains the logic of generating multiple parallel running jobs
        The keys of each dictionary should be the keyword arguments to
        `self._create_jobs()`

        """
        try:
            return self._generation_jobs_inputs
        except AttributeError:
            logger.debug("Generating list of generation jobs")
            jobs_numbers = range(self.inputs.n_level_A_jobs)
            jobs_inputs = []
            for idx in jobs_numbers:
                ji = JobInput(
                    idx=idx, meta_label=self.inputs.level_A_labels[idx], kwargs=dict()
                )
                jobs_inputs.append(ji)
            logger.debug("List of job inputs = {}".format(jobs_inputs))
            self._generation_jobs_inputs = jobs_inputs
            return jobs_inputs

    def create_generation_jobs(self):
        """ Create all the condor jobs and add them to the dag """

        if self.inputs.local_generation:
            logger.info(
                "Data generation done locally: please do not use this when "
                "submitting a large number of jobs"
            )
            universe = "local"
        else:
            logger.debug(
                "All data will be grabbed in the {} universe".format(self.universe)
            )
            universe = self.universe

        for job_input in self.generation_jobs_inputs:
            self.generation_jobs.append(
                self._create_generation_job(job_input, universe=universe)
            )

    def _create_generation_job(self, job_input, universe):
        """ Create a generation condor job to generate the data

        Parameters
        ----------
        job_input: JobInput
            A NamedTuple holding the specifics of the job input
        universe: str
            The condor universe string

        """

        idx = job_input.idx
        job_name = "_".join([self.inputs.label, "generation", str(idx)])
        if job_input.meta_label is not None:
            job_name = "_".join([job_name, job_input.meta_label])
        job_name = job_name.replace(".", "-")
        submit = self.inputs.submit_directory
        extra_lines = list(self.extra_lines)
        requirements = [self.requirements] if self.requirements else []

        extra_lines.extend(
            self._log_output_error_submit_lines(
                self.inputs.data_generation_log_directory, job_name
            )
        )
        extra_lines.append("accounting_group = {}".format(self.inputs.accounting))

        if universe != "local" and self.inputs.osg:
            _osg_lines, _osg_reqs = self._osg_submit_options(
                self.generation_executable, has_ligo_frames=True
            )
            extra_lines.extend(_osg_lines)
            requirements.append(_osg_reqs)

        arguments = ArgumentsString()
        if self.inputs.use_singularity:
            arguments.append(
                "run --app generation {}".format(self.inputs.singularity_image)
            )
        arguments.add_positional_argument(self.inputs.ini)
        arguments.add("label", job_name)
        self.generation_job_labels.append(job_name)
        arguments.add("idx", idx)
        arguments.add("cluster", "$(Cluster)")
        arguments.add("process", "$(Process)")
        if self.inputs.injection_file is not None:
            arguments.add("injection-file", self.inputs.injection_file)
        arguments.add_unknown_args(self.inputs.unknown_args)
        arguments.add_command_line_arguments()
        generation_job = pycondor.Job(
            name=job_name,
            executable=self.generation_executable,
            submit=submit,
            request_memory=self.inputs.request_memory_generation,
            request_disk=self.request_disk,
            request_cpus=1,
            getenv=self.getenv,
            universe=universe,
            initialdir=self.initialdir,
            notification=self.notification,
            requirements=" && ".join(requirements),
            extra_lines=extra_lines,
            dag=self.dag,
            arguments=arguments.print(),
            retry=self.retry,
            verbose=self.verbose,
        )
        logger.debug("Adding job: {}".format(job_name))

        if self.inputs.run_local:
            subprocess.run(
                [self.generation_executable] + arguments.argument_list, check=True
            )

        return generation_job

    def create_analysis_jobs(self):
        """ Create all the condor jobs and add them to the dag """
        for job_input in self.analysis_jobs_inputs:
            self.analysis_jobs.append(self._create_analysis_job(job_input))

    @property
    def analysis_jobs_inputs(self):
        """ A list of dictionaries enumerating all the main jobs to generate
        This contains the logic of generating multiple parallel running jobs
        The keys of each dictionary should be the keyword arguments to
        `self._create_jobs()`

        """
        logger.debug("Generating list of jobs")

        # Create level B inputs
        detectors_list = []
        detectors_list.append(self.inputs.detectors)
        if self.inputs.coherence_test:
            for detector in self.inputs.detectors:
                detectors_list.append([detector])
        sampler_list = self.inputs.sampler
        n_parallel = self.inputs.n_parallel
        level_B_prod_list = list(
            itertools.product(detectors_list, sampler_list, range(n_parallel))
        )

        level_A_jobs_numbers = range(self.inputs.n_level_A_jobs)
        jobs_inputs = []
        for idx in list(level_A_jobs_numbers):
            for detectors, sampler, run_id in level_B_prod_list:
                jobs_inputs.append(
                    JobInput(
                        idx=idx,
                        meta_label=self.inputs.level_A_labels[idx],
                        kwargs=dict(
                            detectors=detectors, sampler=sampler, run_id=str(run_id)
                        ),
                    )
                )

        logger.debug("List of job inputs = {}".format(jobs_inputs))
        return jobs_inputs

    def _create_analysis_job(self, job_input):
        """ Create an analysis condor job and add it to the dag

        Parameters
        ----------
        job_input: JobInput
            A NamedTuple holding the specifics of the job input

        """
        detectors = job_input.kwargs["detectors"]
        sampler = job_input.kwargs["sampler"]
        run_id = job_input.kwargs["run_id"]
        idx = job_input.idx
        if not isinstance(detectors, list):
            raise BilbyPipeError("`detectors must be a list")

        job_name = "_".join([self.inputs.label, "".join(detectors), sampler])
        if job_input.meta_label is not None:
            job_name = "_".join([job_name, job_input.meta_label])
        job_name = job_name.replace(".", "-")
        job_name += "_{}".format(run_id)
        submit = self.inputs.submit_directory
        requirements = [self.requirements] if self.requirements else []
        extra_lines = list(self.extra_lines)
        extra_lines.extend(
            self._log_output_error_submit_lines(
                self.inputs.data_analysis_log_directory, job_name
            )
            + self._checkpoint_submit_lines()
            + ["accounting_group = {}".format(self.inputs.accounting)]
        )

        if self.inputs.transfer_files or self.inputs.osg:
            data_dump_file = DataDump.get_filename(
                self.inputs.data_directory, self.generation_job_labels[idx], idx
            )
            input_files_to_transfer = [
                str(data_dump_file),
                str(self.inputs.prior_file),
                str(self.inputs.ini),
            ]
            distance_marg_cache_file = ".distance_marginalization_lookup.npz"
            if os.path.isfile(distance_marg_cache_file):
                input_files_to_transfer.append(distance_marg_cache_file)
            extra_lines.extend(
                self._condor_file_transfer_lines(
                    input_files_to_transfer,
                    [self._relative_topdir(self.inputs.outdir, self.initialdir)],
                )
            )

        if self.inputs.osg:
            _osg_lines, _osg_reqs = self._osg_submit_options(self.analysis_executable)
            extra_lines.extend(_osg_lines)
            requirements.append(_osg_reqs)

        arguments = ArgumentsString()
        if self.inputs.use_singularity:
            arguments.append(
                "run --app analysis {}".format(self.inputs.singularity_image)
            )
        arguments.add_positional_argument(self.inputs.ini)
        for detector in detectors:
            arguments.add("detectors", detector)
        arguments.add("label", job_name)
        self.analysis_job_labels.append(job_name)
        arguments.add("data-label", self.generation_job_labels[idx])
        arguments.add("idx", idx)
        arguments.add("sampler", sampler)
        arguments.add("cluster", "$(Cluster)")
        arguments.add("process", "$(Process)")
        arguments.add_unknown_args(self.inputs.unknown_args)
        arguments.add_command_line_arguments()
        job = pycondor.Job(
            name=job_name,
            executable=self.analysis_executable,
            submit=submit,
            request_memory=self.inputs.request_memory,
            request_disk=self.request_disk,
            request_cpus=self.request_cpus,
            getenv=self.getenv,
            universe=self.universe,
            initialdir=self.initialdir,
            notification=self.notification,
            requirements=" && ".join(requirements),
            extra_lines=extra_lines,
            dag=self.dag,
            arguments=arguments.print(),
            retry=self.retry,
            verbose=self.verbose,
        )
        job.add_parent(self.generation_jobs[idx])
        logger.debug("Adding job: {}".format(job_name))
        self.results_pages[job_name] = "result/{}.html".format(job_name)

        if self.inputs.run_local:
            subprocess.run([self.analysis_executable] + arguments.argument_list)

        return job

    def create_postprocessing_jobs(self):
        """ Generate postprocessing job """
        if self.inputs.postprocessing_arguments is None:
            logger.debug("No postprocessing job requested")
            return

        job_name = "{}_postprocessing".format(self.inputs.label)
        submit = self.inputs.submit_directory
        extra_lines = list(self.extra_lines)
        requirements = [self.requirements] if self.requirements else []
        extra_lines.extend(
            self._log_output_error_submit_lines(
                self.inputs.data_analysis_log_directory, job_name
            )
            + ["accounting_group = {}".format(self.inputs.accounting)]
        )

        exe = shutil.which(self.inputs.postprocessing_executable)

        if self.inputs.osg:
            _osg_lines, _osg_reqs = self._osg_submit_options(exe)
            extra_lines.extend(_osg_lines)
            requirements.append(_osg_reqs)

        job = pycondor.Job(
            name=job_name,
            executable=exe,
            submit=submit,
            getenv=self.getenv,
            universe=self.universe,
            initialdir=self.initialdir,
            notification=self.notification,
            requirements=" && ".join(requirements),
            dag=self.dag,
            extra_lines=extra_lines,
            arguments=self.inputs.postprocessing_arguments,
            retry=self.retry,
            verbose=self.verbose,
        )
        for analysis_job in self.analysis_jobs:
            job.add_parent(analysis_job)
        logger.debug("Adding postprocessing job")

    @property
    def result_files_list(self):
        """ Returns the list of expected results files """
        return [
            "{}/{}_result.json".format(self.inputs.result_directory, lab)
            for lab in self.analysis_job_labels
        ]

    @property
    def merged_runs_label(self):
        return self.inputs.label + "_combined"

    @property
    def merged_runs_result_file(self):
        return "{}/{}_result.json".format(
            self.inputs.result_directory, self.merged_runs_label
        )

    def create_merge_runs_job(self):
        if self.inputs.n_parallel < 2:
            self.merged_runs = False
            return
        job_name = "_".join([self.inputs.label, "merge_runs"])
        submit = self.inputs.submit_directory
        extra_lines = list(self.extra_lines)
        requirements = [self.requirements] if self.requirements else []

        extra_lines.extend(
            self._log_output_error_submit_lines(
                self.inputs.data_analysis_log_directory, job_name
            )
            + ["accounting_group = {}".format(self.inputs.accounting)]
        )

        exe = shutil.which("bilby_result")
        arguments = "-r {} --merge --outdir {} --label {}".format(
            " ".join(self.result_files_list),
            self.inputs.result_directory,
            self.merged_runs_label,
        )

        if self.inputs.osg:
            _osg_lines, _osg_reqs = self._osg_submit_options(exe)
            extra_lines.extend(_osg_lines)
            requirements.append(_osg_reqs)

        job = pycondor.Job(
            name=job_name,
            executable=exe,
            submit=submit,
            getenv=self.getenv,
            universe=self.universe,
            initialdir=self.initialdir,
            notification=self.notification,
            requirements=" && ".join(requirements),
            dag=self.dag,
            extra_lines=extra_lines,
            arguments=arguments,
            retry=self.retry,
            verbose=self.verbose,
        )
        for analysis_job in self.analysis_jobs:
            job.add_parent(analysis_job)
        self.merged_runs = True
        self.merged_runs_job = job
        logger.debug("Adding merge-runs job")

    def create_plot_jobs(self):

        if self.inputs.local_plot:
            universe = "local"
        else:
            universe = self.universe

        if self.merged_runs:
            files = [self.merged_runs_result_file]
            parent_jobs = [self.merged_runs_job]
        else:
            files = self.result_files_list
            parent_jobs = self.analysis_jobs

        for file, parent_job in zip(files, parent_jobs):
            job_name = parent_job.name + "_plot"
            extra_lines = list(self.extra_lines)
            extra_lines.extend(
                self._log_output_error_submit_lines(
                    self.inputs.data_analysis_log_directory, job_name
                )
                + ["accounting_group = {}".format(self.inputs.accounting)]
            )

            arguments = ArgumentsString()
            arguments.add_positional_argument(self.inputs.ini)
            arguments.add("result", file)

            job = pycondor.Job(
                name=job_name,
                executable=shutil.which("bilby_pipe_plot"),
                submit=self.inputs.submit_directory,
                request_memory="64 GB",
                getenv=self.getenv,
                universe=universe,
                initialdir=self.initialdir,
                notification=self.notification,
                requirements=self.requirements,
                dag=self.dag,
                extra_lines=extra_lines,
                arguments=arguments.print(),
                retry=self.retry,
                verbose=self.verbose,
            )
            job.add_parent(parent_job)
            logger.debug("Adding plot job")

    def create_summary_jobs(self):
        """ Create a condor job for pesummary and add it to the dag """
        logger.debug("Generating pesummary jobs")

        if self.merged_runs:
            files = [self.merged_runs_result_file]
            parent_jobs = [self.merged_runs_job]
        else:
            files = self.result_files_list
            parent_jobs = self.analysis_jobs

        webdir = self.inputs.webdir
        email = self.inputs.email
        existing_dir = self.inputs.existing_dir
        job_name = "_".join([self.inputs.label, "results_page"])
        job_name = job_name.replace(".", "-")
        submit = self.inputs.submit_directory
        extra_lines = list(self.extra_lines)
        requirements = [self.requirements] if self.requirements else []

        extra_lines.extend(
            self._log_output_error_submit_lines(
                self.inputs.summary_log_directory, job_name
            )
            + ["accounting_group = {}".format(self.inputs.accounting)]
        )

        if self.inputs.transfer_files or self.inputs.osg:
            extra_lines.extend(
                self._condor_file_transfer_lines(
                    [str(self.inputs.ini)] + files,
                    [self._relative_topdir(self.inputs.outdir, self.initialdir)],
                )
            )
            # condor transfers all files into a flat structure
            files = list(map(os.path.basename, files))

        if self.inputs.osg:
            _osg_lines, _osg_reqs = self._osg_submit_options(self.summary_executable)
            extra_lines.extend(_osg_lines)
            requirements.append(_osg_reqs)

        arguments = ArgumentsString()
        arguments.add("webdir", webdir)
        arguments.add("email", email)
        arguments.add("config", " ".join([self.inputs.ini] * len(files)))
        arguments.add("samples", " ".join(files))
        arguments.append(
            "-a {}".format(" ".join([self.inputs.waveform_approximant] * len(files)))
        )
        arguments.append(
            "--labels {}".format(" ".join([os.path.basename(f) for f in files]))
        )
        if existing_dir is not None:
            arguments.add("existing_webdir", existing_dir)

        job = pycondor.Job(
            name=job_name,
            executable=self.summary_executable,
            submit=submit,
            request_memory=self.inputs.request_memory,
            request_disk=self.request_disk,
            request_cpus=self.request_cpus,
            getenv=self.getenv,
            universe=self.universe,
            initialdir=self.initialdir,
            notification=self.notification,
            requirements=" && ".join(requirements),
            extra_lines=extra_lines,
            dag=self.dag,
            arguments=arguments.print(),
            retry=self.retry,
            verbose=self.verbose,
        )
        for parent_job in parent_jobs:
            job.add_parent(parent_job)
        logger.debug("Adding job: {}".format(job_name))

    def build_condor_dag(self):
        """ Build the dag, optionally submit them if requested in inputs """
        submitted = False
        if self.inputs.submit:
            try:
                self.dag.build_submit()
                submitted = True
            except OSError:
                logger.warning("Unable to submit files")
                self.dag.build()
        else:
            self.dag.build()

        if submitted:
            logger.info("DAG generation complete and submitted")
        else:
            command_line = "$ condor_submit_dag {}".format(
                os.path.relpath(self.dag.submit_file)
            )
            logger.info(
                "DAG generation complete, to submit jobs run:\n  {}".format(
                    command_line
                )
            )

    def build_slurm_submit(self):
        """ Build slurm submission scripts """

        slurm.SubmitSLURM(self)

    def write_bash_script(self):
        """
        Write the dag to a bash script so jobs can be easily run on the command
        line.
        """
        with open(self.bash_file, "w") as ff:
            ff.write("#!/usr/bin/env bash\n\n")
            for node in self.dag.nodes:
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
                job_str = job_str.replace("$(Cluster)", "0")
                job_str = job_str.replace("$(Process)", "0")
                ff.write(job_str)

    @property
    def bash_file(self):
        bash_file = self.dag.submit_file.replace(".submit", ".sh").replace(
            "dag_", "bash_"
        )
        return bash_file

    @staticmethod
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
        ['log = test/job_$(Cluster)_$(Process).log',
         'output = test/job_$(Cluster)_$(Process).out',
         'error = test/job_$(Cluster)_$(Process).err']
        """
        logpath = Path(logdir)
        filename = "{}_$(Cluster)_$(Process).{{}}".format(prefix)
        return [
            "{} = {}".format(opt, str(logpath / filename.format(opt[:3])))
            for opt in ("log", "output", "error")
        ]

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

        # if we need singularity:
        if self.inputs.use_singularity:
            requirements.append("(HAS_SINGULARITY=?=True)")
        # otherwise if need the ligo-containers /cvmfs repo:
        elif executable.startswith("/cvmfs/ligo-containers.opensciencegrid.org"):
            requirements.append("(HAS_CVMFS_LIGO_CONTAINERS=?=True)")

        return lines, " && ".join(requirements)


def main():
    """ Top-level interface for bilby_pipe """
    parser = create_parser(top_level=True)
    args, unknown_args = parse_args(get_command_line_arguments(), parser)
    log_version_information()

    inputs = MainInput(args, unknown_args)

    args.outdir = os.path.abspath(args.outdir)
    complete_ini_file = "{}/{}_config_complete.ini".format(inputs.outdir, inputs.label)
    parser.write_to_file(
        filename=complete_ini_file,
        args=args,
        overwrite=False,
        include_description=False,
    )

    Dag(inputs)

    if len(unknown_args) > 1:
        logger.warning(
            tcolors.WARNING
            + "Unrecognized arguments {}".format(unknown_args)
            + tcolors.END
        )
