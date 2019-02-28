#!/usr/bin/env python
"""
bilby_pipe is a command line tools for taking user input (as command line
arguments or an ini file) and creating DAG files for submitting bilby parameter
estimation jobs.
"""
import os
import sys
import shutil
import subprocess
import itertools
from collections import namedtuple
import pickle

import pycondor

from .utils import logger, parse_args, BilbyPipeError
from . import utils
from . import create_injections
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
        A list of the arguments to parse. Defauts to `sys.argv[1:]`

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
    x509userproxy: str
        A path to the users X509 certificate used for authentication

    """

    def __init__(self, args, unknown_args):
        logger.debug("Creating new Input object")
        logger.info("Command line arguments: {}".format(args))

        logger.debug("Known detector list = {}".format(self.known_detectors))

        self.unknown_args = unknown_args
        self.ini = args.ini
        self.submit = args.submit
        self.singularity_image = args.singularity_image
        self.outdir = args.outdir
        self.label = args.label
        self.queue = 1
        self.create_summary = args.create_summary
        self.accounting = args.accounting
        self.sampler = args.sampler
        self.detectors = args.detectors
        self.coherence_test = args.coherence_test
        self.x509userproxy = args.X509

        self.waveform_approximant = args.waveform_approximant

        self.webdir = args.webdir
        self.email = args.email
        self.existing_dir = args.existing_dir

        self.run_local = args.local
        self.local_generation = args.local_generation

        self.gps_file = args.gps_file

        self.injection = args.injection
        self.injection_file = args.injection_file
        self.n_injection = args.n_injection

        self.gracedb = args.gracedb
        self.trigger_time = args.trigger_time

        # These keys are used in the webpages summary
        self.meta_keys = [
            "label",
            "outdir",
            "ini",
            "detectors",
            "coherence_test",
            "sampler",
            "accounting",
        ]

        self.request_memory = args.request_memory
        self.request_cpus = args.request_cpus

    @property
    def ini(self):
        return self._ini

    @ini.setter
    def ini(self, ini):
        if os.path.isfile(ini) is False:
            raise BilbyPipeError("ini file is not a file")
        self._ini = os.path.abspath(ini)

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
        try:
            return self._n_level_A_jobs
        except AttributeError:
            logger.debug("n_level_A_jobs not set, defaulting to 1")
            return 1

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

    @property
    def x509userproxy(self):
        """ A path to the users X509 certificate used for authentication """
        try:
            return self._x509userproxy
        except AttributeError:
            raise BilbyPipeError(
                "The X509 user proxy has not been correctly set, please check"
                " the logs"
            )

    @x509userproxy.setter
    def x509userproxy(self, x509userproxy):
        if x509userproxy is None:
            cert_alias = "X509_USER_PROXY"
            try:
                cert_path = os.environ[cert_alias]
                new_cert_path = os.path.join(
                    self.outdir, "." + os.path.basename(cert_path)
                )
                shutil.copyfile(cert_path, new_cert_path)
                self._x509userproxy = new_cert_path
            except FileNotFoundError:
                logger.warning(
                    "Environment variable X509_USER_PROXY does not point to a"
                    " file. Try running `$ ligo-proxy-init albert.einstein`"
                )
            except KeyError:
                logger.warning(
                    "Environment variable X509_USER_PROXY not set"
                    " Try running `$ ligo-proxy-init albert.einstein`"
                )
                self._x509userproxy = None
        elif os.path.isfile(x509userproxy):
            self._x509userproxy = x509userproxy
        else:
            raise BilbyPipeError("Input X509 not a file or not understood")

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

    @property
    def n_injection(self):
        return self._n_injection

    @n_injection.setter
    def n_injection(self, n_injection):
        if n_injection is not None:
            logger.info("n_injection={}, setting level A jobs".format(n_injection))
            self.n_level_A_jobs = n_injection
            self._n_injection = n_injection
            self.level_A_labels = ["injection_{}".format(x) for x in range(n_injection)]
        else:
            self._n_injection = None

    @property
    def gracedb(self):
        return self._gracedb

    @gracedb.setter
    def gracedb(self, gracedb):
        if gracedb is not None:
            self._gracedb = gracedb
            self.level_A_labels = [gracedb]
        else:
            self._gracedb = None

    @property
    def trigger_time(self):
        return self._trigger_time

    @trigger_time.setter
    def trigger_time(self, trigger_time):
        if trigger_time is not None:
            self._trigger_time = trigger_time
            self.level_A_labels = [str(trigger_time)]
        else:
            self._trigger_time = None

    @property
    def request_memory(self):
        return self._request_memory

    @request_memory.setter
    def request_memory(self, request_memory):
        logger.info("request_memory = {} GB".format(request_memory))
        self._request_memory = "{} GB".format(request_memory)

    @property
    def request_cpus(self):
        return self._request_cpus

    @request_cpus.setter
    def request_cpus(self, request_cpus):
        logger.info("request_cpus = {}".format(request_cpus))
        self._request_cpus = request_cpus


class Dag(object):
    """ A class to handle the creation and building of a DAG

    Parameters
    ----------
    inputs: bilby_pipe.Input
        An object holding the inputs built from the command-line and ini file.

    Other parameters
    ----------------
    request_memory : str or None, optional
        Memory request to be included in submit file.
        request_disk : str or None, optional
        Disk request to be included in submit file.
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
        initialdir=None,
        notification="never",
        requirements=None,
        retry=None,
        verbose=0,
    ):
        self.request_memory = inputs.request_memory
        self.request_disk = request_disk
        self.request_cpus = inputs.request_cpus
        self.getenv = getenv
        self.universe = universe
        self.initialdir = initialdir
        self.notification = notification
        self.requirements = requirements
        self.retry = retry
        self.verbose = verbose
        self.inputs = inputs

        self.dag_name = "dag_{}".format(inputs.label)
        self.dag = pycondor.Dagman(
            name=self.dag_name, submit=self.inputs.submit_directory
        )

        self.generation_jobs = []
        self.generation_job_labels = []
        self.analysis_jobs = []
        self.summary_jobs = []
        self.results_pages = dict()
        if self.inputs.injection:
            self.check_injection()
        self.create_generation_jobs()
        self.create_analysis_jobs()
        self.create_postprocessing_jobs()
        if self.inputs.create_summary:
            self.create_summary_jobs()
        self.build_submit()

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
            # This hard-codes the path to singularity: TODO infer this from the users env
            return "/bin/singularity"
        else:
            return self._get_executable_path("bilby_pipe_generation")

    @property
    def analysis_executable(self):
        if self.inputs.use_singularity:
            # This hard-codes the path to singularity: TODO infer this from the users env
            return "/bin/singularity"
        else:
            return self._get_executable_path("bilby_pipe_analysis")

    @property
    def summary_executable(self):
        return self._get_executable_path("summarypages.py")

    def check_injection(self):
        """ If injections are requested, create an injection file """
        default_injection_file_name = "{}/{}_injection_file.h5".format(
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
            inj_inputs = create_injections.CreateInjectionInput(
                inj_args, inj_unknown_args
            )
            inj_inputs.create_injection_file(default_injection_file_name)
            self.inputs.injection_file = default_injection_file_name

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
            logger.info("All data will be grabbed in the local universe")
            universe = "local"
        else:
            logger.info(
                "All data will be grabbed in the {} universe".format(self.universe)
            )
            universe = self.universe

        for job_input in self.generation_jobs_inputs:
            self.generation_jobs.append(
                self._create_generation_job(job_input, universe=universe)
            )

    def _create_generation_job(self, job_input, universe):
        """ Create a job to generate the data """
        idx = job_input.idx
        job_name = "_".join([self.inputs.label, "generation", str(idx)])
        if job_input.meta_label is not None:
            job_name = "_".join([job_name, job_input.meta_label])
        job_name = job_name.replace(".", "-")
        job_logs_base = os.path.join(
            self.inputs.data_generation_log_directory, job_name
        )
        submit = self.inputs.submit_directory
        extra_lines = ""
        for arg in ["error", "log", "output"]:
            extra_lines += "\n{} = {}_$(Cluster)_$(Process).{}".format(
                arg, job_logs_base, arg[:3]
            )
        extra_lines += "\naccounting_group = {}".format(self.inputs.accounting)
        extra_lines += "\nx509userproxy = {}".format(self.inputs.x509userproxy)

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
            request_memory=self.request_memory,
            request_disk=self.request_disk,
            request_cpus=self.request_cpus,
            getenv=self.getenv,
            universe=universe,
            initialdir=self.initialdir,
            notification=self.notification,
            requirements=self.requirements,
            queue=self.inputs.queue,
            extra_lines=extra_lines,
            dag=self.dag,
            arguments=arguments.print(),
            retry=self.retry,
            verbose=self.verbose,
        )
        logger.debug("Adding job: {}".format(job_name))

        if self.inputs.run_local:
            subprocess.run([self.generation_executable] + arguments.argument_list)

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
        level_B_prod_list = list(itertools.product(detectors_list, sampler_list))

        level_A_jobs_numbers = range(self.inputs.n_level_A_jobs)
        jobs_inputs = []
        for idx in list(level_A_jobs_numbers):
            for detectors, sampler in level_B_prod_list:
                jobs_inputs.append(
                    JobInput(
                        idx=idx,
                        meta_label=self.inputs.level_A_labels[idx],
                        kwargs=dict(detectors=detectors, sampler=sampler),
                    )
                )

        logger.debug("List of job inputs = {}".format(jobs_inputs))
        return jobs_inputs

    def _create_analysis_job(self, job_input):
        """ Create a condor job and add it to the dag

        Parameters
        ----------
        detectors: list, str
            A list of the detectors to include, e.g. `['H1', 'L1']`
        sampler: str
            The sampler to use for the job

        """
        detectors = job_input.kwargs["detectors"]
        sampler = job_input.kwargs["sampler"]
        idx = job_input.idx
        if not isinstance(detectors, list):
            raise BilbyPipeError("`detectors must be a list")

        job_name = "_".join([self.inputs.label, "".join(detectors), sampler])
        if job_input.meta_label is not None:
            job_name = "_".join([job_name, job_input.meta_label])
        job_name = job_name.replace(".", "-")
        job_logs_base = os.path.join(self.inputs.data_analysis_log_directory, job_name)
        submit = self.inputs.submit_directory
        extra_lines = ""
        for arg in ["error", "log", "output"]:
            extra_lines += "\n{} = {}_$(Cluster)_$(Process).{}".format(
                arg, job_logs_base, arg[:3]
            )
        extra_lines += "\naccounting_group = {}".format(self.inputs.accounting)
        extra_lines += "\nx509userproxy = {}".format(self.inputs.x509userproxy)

        arguments = ArgumentsString()
        if self.inputs.use_singularity:
            arguments.append(
                "run --app analysis {}".format(self.inputs.singularity_image)
            )
        arguments.add_positional_argument(self.inputs.ini)
        for detector in detectors:
            arguments.add("detectors", detector)
        arguments.add("label", job_name)
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
            request_memory=self.request_memory,
            request_disk=self.request_disk,
            request_cpus=self.request_cpus,
            getenv=self.getenv,
            universe=self.universe,
            initialdir=self.initialdir,
            notification=self.notification,
            requirements=self.requirements,
            queue=self.inputs.queue,
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
        pass

    @property
    def summary_jobs_inputs(self):
        """ A list of dictionaries enumerating all the main jobs to generate

        This contains the logic of generating multiple parallel running jobs
        The keys of each dictionary should be the keyword arguments to
        `self._create_jobs()`

        """
        logger.debug("Generating list of jobs")

        # Create level B inputs
        sampler = self.inputs.sampler
        webdir = self.inputs.webdir
        email = self.inputs.email
        existing_dir = self.inputs.existing_dir

        detectors_list = []
        detectors_list.append(self.inputs.detectors)
        if self.inputs.coherence_test:
            for detector in self.inputs.detectors:
                detectors_list.append([detector])
        level_B_prod_list = self.inputs.sampler

        level_A_jobs_numbers = range(self.inputs.n_level_A_jobs)
        jobs_inputs = []
        for idx in list(level_A_jobs_numbers):
            for sampler in level_B_prod_list:
                jobs_inputs.append(
                    JobInput(
                        idx=idx,
                        meta_label=self.inputs.level_A_labels[idx],
                        kwargs=dict(
                            detectors_list=detectors_list,
                            sampler=sampler,
                            webdir=webdir,
                            email=email,
                            existing_dir=existing_dir,
                        ),
                    )
                )

        logger.debug("List of job inputs = {}".format(jobs_inputs))
        return jobs_inputs

    def create_summary_jobs(self):
        """ Generate job to generate summary pages """
        for job_input in self.summary_jobs_inputs:
            self.summary_jobs.append(self._create_summary_job(job_input))

    def _create_summary_job(self, job_input):
        """ Create a condor job for pesummary and add it to the dag """
        webdir = job_input.kwargs["webdir"]
        email = job_input.kwargs["email"]
        detectors_list = job_input.kwargs["detectors_list"]
        sampler = job_input.kwargs["sampler"]
        existing_dir = job_input.kwargs["existing_dir"]
        idx = job_input.idx
        base_path = self.inputs.result_directory + "/"
        result_files = [
            base_path
            + "_".join(
                [self.inputs.label, "".join(i), sampler, job_input.meta_label, "result"]
            )
            + ".h5"
            for i in detectors_list
        ]
        job_name = "_".join([self.inputs.label, "results_page", str(idx)])
        if job_input.meta_label is not None:
            job_name = "_".join([job_name, job_input.meta_label])
        job_name = job_name.replace(".", "-")
        job_logs_base = os.path.join(self.inputs.summary_log_directory, job_name)
        submit = self.inputs.submit_directory
        extra_lines = ""
        for arg in ["error", "log", "output"]:
            extra_lines += "\n{} = {}_$(Cluster)_$(Process).{}".format(
                arg, job_logs_base, arg[:3]
            )
        extra_lines += "\naccounting_group = {}".format(self.inputs.accounting)
        extra_lines += "\nx509userproxy = {}".format(self.inputs.x509userproxy)
        arguments = ArgumentsString()
        arguments.add("webdir", webdir)
        arguments.add("email", email)
        arguments.add("config", " ".join([self.inputs.ini] * len(result_files)))
        arguments.add("samples", " ".join(result_files))
        arguments.append(
            "-a {}".format(
                " ".join([self.inputs.waveform_approximant] * len(result_files))
            )
        )
        if existing_dir is not None:
            arguments.add("existing_webdir", existing_dir)

        job = pycondor.Job(
            name=job_name,
            executable=self.summary_executable,
            submit=submit,
            request_memory=self.request_memory,
            request_disk=self.request_disk,
            request_cpus=self.request_cpus,
            getenv=self.getenv,
            universe=self.universe,
            initialdir=self.initialdir,
            notification=self.notification,
            requirements=self.requirements,
            queue=self.inputs.queue,
            extra_lines=extra_lines,
            dag=self.dag,
            arguments=arguments.print(),
            retry=self.retry,
            verbose=self.verbose,
        )
        job.add_parent(self.analysis_jobs[idx])
        logger.debug("Adding job: {}".format(job_name))

    def build_submit(self):
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


class ArgumentsString(object):
    """ A convienience object to aid in the creation of argument strings """

    def __init__(self):
        self.argument_list = []

    def append(self, argument):
        self.argument_list.append(argument)

    def add_positional_argument(self, value):
        self.argument_list.append("{}".format(value))

    def add(self, argument, value):
        self.argument_list.append("--{}".format(argument))
        self.argument_list.append("{}".format(value))

    def add_unknown_args(self, unknown_args):
        self.argument_list += unknown_args

    def add_command_line_arguments(self):
        """ Adds command line arguments given in addition to the ini file """
        command_line_args_list = utils.get_command_line_arguments()
        # Remove the first positional ini-file argument
        command_line_args_list = command_line_args_list[1:]
        self.argument_list += command_line_args_list

    def print(self):
        return " ".join(self.argument_list)


class DataDump(object):
    def __init__(self, label, outdir, trigger_time, interferometers, meta_data, idx):
        self.trigger_time = trigger_time
        self.label = label
        self.outdir = outdir
        self.interferometers = interferometers
        self.meta_data = meta_data
        self.idx = idx

    @staticmethod
    def get_filename(outdir, label, idx):
        return os.path.join(outdir, "_".join([label, str(idx), "data_dump.pickle"]))

    @property
    def filename(self):
        return self.get_filename(self.outdir, self.label, self.idx)

    def to_pickle(self):
        with open(self.filename, "wb+") as file:
            pickle.dump(self, file)

    @classmethod
    def from_pickle(cls, filename=None):
        """ Loads in a data dump

        Parameters
        ----------
        filename: str
            If given, try to load from this filename

        """
        with open(filename, "rb") as file:
            res = pickle.load(file)
        if res.__class__ == list:
            res = cls(res)
        if res.__class__ != cls:
            raise TypeError("The loaded object is not a DataDump")
        return res


def create_main_parser():
    return create_parser(
        pipe_args=True,
        job_args=True,
        run_spec=True,
        pe_summary=True,
        injection=True,
        data_gen=True,
        waveform=True,
        generation=False,
        analysis=False,
    )


def main():
    """ Top-level interface for bilby_pipe """
    args, unknown_args = parse_args(
        utils.get_command_line_arguments(), create_main_parser()
    )
    inputs = MainInput(args, unknown_args)
    # Create a Directed Acyclic Graph (DAG) of the workflow
    Dag(inputs)
