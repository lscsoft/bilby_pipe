import os
import sys

import pycondor

from ..utils import logger
from . import slurm


class Dag(object):
    """ Base Dag object, handles the creation of the DAG structure """

    def __init__(self, inputs):
        self.inputs = inputs
        self.dag_name = "dag_{}".format(inputs.label)
        self.submit_directory = inputs.submit_directory

        self.scheduler = self.inputs.scheduler
        self.scheduler_args = self.inputs.scheduler_args
        self.scheduler_module = self.inputs.scheduler_module
        self.scheduler_env = self.inputs.scheduler_env
        self.scheduler_analysis_time = self.inputs.scheduler_analysis_time

        # The slurm setup uses the pycondor dag as a base
        if self.scheduler.lower() in ["condor", "slurm"]:
            self.setup_pycondor_dag()

    def setup_pycondor_dag(self):
        self.pycondor_dag = pycondor.Dagman(
            name=self.dag_name, submit=self.submit_directory
        )

    def build(self):
        if self.inputs.scheduler.lower() == "condor":
            self.build_pycondor_dag()
        elif self.inputs.scheduler.lower() == "slurm":
            self.build_slurm_submit()

        self.write_bash_script()

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
                        self.submit_directory, self.pycondor_dag.name
                    )
                )
            except Exception:
                pass

    def build_slurm_submit(self):
        """ Build slurm submission scripts """

        _slurm = slurm.SubmitSLURM(self)
        if self.inputs.local_generation:
            _slurm.run_local_generation()
        _slurm.write_master_slurm()

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
        return "{}/bash_{}.sh".format(self.submit_directory, self.inputs.label)
