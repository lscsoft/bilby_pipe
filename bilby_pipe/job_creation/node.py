import os
import re
import shutil
import subprocess
from pathlib import Path

import pycondor

from ..utils import CHECKPOINT_EXIT_CODE, ArgumentsString, BilbyPipeError, logger


class Node(object):
    """ Base Node object, handles creation of arguments, executables, etc """

    def __init__(self, inputs):
        self.inputs = inputs
        self._universe = "vanilla"
        self.request_disk = None
        self.online_pe = self.inputs.online_pe
        self.getenv = True
        self.notification = inputs.notification
        self.retry = None
        self.verbose = 0
        self.condor_job_priority = inputs.condor_job_priority
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
            raise OSError(f"{exe_name} not installed on this system, unable to proceed")

    def setup_arguments(
        self,
        parallel_program=None,
        add_command_line_args=True,
        add_ini=True,
        add_unknown_args=True,
    ):
        self.arguments = ArgumentsString()
        if parallel_program is not None:
            self.arguments.add("np", self.inputs.request_cpus)
            self.arguments.add_positional_argument(parallel_program)
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

        if self.inputs.scheduler.lower() == "condor":
            self.add_accounting()

        self.extra_lines.append(f"priority = {self.condor_job_priority}")
        if self.inputs.email is not None:
            self.extra_lines.append(f"notify_user = {self.inputs.email}")

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
            request_cpus=self.request_cpus,
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

        # Hack to allow passing walltime down to slurm
        setattr(self.job, "slurm_walltime", self.slurm_walltime)

        logger.debug(f"Adding job: {job_name}")

    def add_accounting(self):
        """ Add the accounting-group extra lines """
        if self.inputs.accounting:
            self.extra_lines.append(f"accounting_group = {self.inputs.accounting}")
        else:
            raise BilbyPipeError(
                "No accounting tag provided - this is required for condor submission"
            )

    @staticmethod
    def _checkpoint_submit_lines():
        return [
            f"+SuccessCheckpointExitCode = {CHECKPOINT_EXIT_CODE}",
            "+WantFTOnCheckpoint = True",
        ]

    @staticmethod
    def _condor_file_transfer_lines(inputs, outputs):
        return [
            "should_transfer_files = YES",
            f"transfer_input_files = {','.join(inputs)}",
            f"transfer_output_files = {','.join(outputs)}",
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
            exc.args = (f"cannot format {path} relative to {reference}",)
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
            requirements.append(f"(HAS_CVMFS_{re.sub('[.-]', '_', repo)}=?=True)")

        return lines, " && ".join(requirements)

    @property
    def slurm_walltime(self):
        """ Default wall-time for base-name """
        # One hour
        return "1:00:00"


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
    filename = f"{prefix}.{{}}"
    return [
        f"{opt} = {str(logpath / filename.format(opt[:3]))}"
        for opt in ("log", "output", "error")
    ]
