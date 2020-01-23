#!/usr/bin/env python
"""
Module containing the tools for outputting slurm submission scripts
"""

from .utils import logger


class SubmitSLURM(object):
    def __init__(self, dag):

        self.dag = dag.pycondor_dag
        self.submit_dir = dag.inputs.submit_directory
        self.label = dag.inputs.label
        self.scheduler = dag.scheduler
        self.scheduler_args = dag.scheduler_args
        self.scheduler_module = dag.scheduler_module
        self.scheduler_env = dag.scheduler_env

        self.write_master_slurm()

    def write_master_slurm(self):
        """
        Translate dag content to SLURM script
        """

        with open(self.slurm_master_bash, "w") as f:

            # reformat slurm options
            if self.scheduler_args is not None:
                slurm_args = " ".join(
                    ["--{}".format(arg) for arg in self.scheduler_args.split()]
                )
            else:
                slurm_args = ""

            f.write("#!/bin/bash \n")

            for arg in slurm_args.split():
                f.write("#SBATCH {} \n".format(arg))

            # write output to standard file
            f.write(
                "#SBATCH --output={}/{}_master_slurm.out \n".format(
                    self.submit_dir, self.label
                )
            )
            f.write(
                "#SBATCH --error={}/{}_master_slurm.err \n".format(
                    self.submit_dir, self.label
                )
            )

            if self.scheduler_module is not None:
                for module in self.scheduler_module:

                    f.write("\nmodule load {}\n".format(module))

            if self.scheduler_env is not None:

                f.write("\nsource activate {}\n".format(self.scheduler_env))

            # assign new job ID to each process
            jids = range(len(self.dag.nodes))

            job_names = [node.name for node in self.dag.nodes]

            # create dict for assigning ID to job name
            job_dict = dict(zip(job_names, jids))

            for node, indx in zip(self.dag.nodes, jids):

                submit_str = "\njid{}=($(sbatch {} ".format(indx, slurm_args)

                # get list of all parents associated with job
                parents = [job.name for job in node.parents]

                if len(parents) > 0:
                    # only run subsequent jobs after parent has
                    # *successfully* completed
                    submit_str += "--dependency=afterok"

                    for parent in parents:
                        submit_str += ":${{jid{}[-1]}}".format(job_dict[parent])
                # get output file path from dag and use for slurm
                output_file = self._output_name_from_dag(node.extra_lines)

                submit_str += " --output={}".format(output_file)
                submit_str += " --error={}".format(output_file.replace(".out", ".err"))

                job_script = self._write_individual_processes(
                    node.name, node.executable, node.args[0].arg
                )

                submit_str += " {}))".format(job_script)

                f.write("{}\n".format(submit_str))

        # print out how to submit
        command_line = "$ sbatch {}".format(self.slurm_master_bash)
        logger.info(
            "SLURM scripts written, to run jobs submit:\n  {}".format(command_line)
        )

    def _write_individual_processes(self, name, executable, args):

        fname = name + ".sh"
        job_path = self.submit_dir + "/" + fname

        with open(job_path, "w") as ff:

            ff.write("#!/bin/bash \n")

            if self.scheduler_module is not None:
                for module in self.scheduler_module:

                    ff.write("\nmodule load {}\n".format(module))

            if self.scheduler_env is not None:

                ff.write("\nsource activate {}\n\n".format(self.scheduler_env))

            job_str = "{} {}\n\n".format(executable, args)

            # get rid of unnecessary arguments
            job_str = job_str.replace(" --cluster $(Cluster)", "")
            job_str = job_str.replace(" --process $(Process)", "")

            job_str = job_str.replace(
                "--scheduler-args {}".format(self.scheduler_args), ""
            )
            if self.scheduler_module is not None:
                job_str = job_str.replace(
                    "--scheduler-module {}".format(" ".join(self.scheduler_module)), ""
                )
            else:
                job_str = job_str.replace(
                    "--scheduler-module {}".format(self.scheduler_module), ""
                )

            job_str = job_str.replace(
                "--scheduler-env {}".format(self.scheduler_env), ""
            )

            job_str = job_str.replace("--scheduler {}".format(self.scheduler), "")

            ff.write(job_str)

        return job_path

    @property
    def slurm_master_bash(self):
        """
        Create filename for master script
        """
        return self.submit_dir + "/" + self.label + "_master_slurm.sh"

    @staticmethod
    def _output_name_from_dag(extra_lines):

        # probably a faster way to do this, but the list is short so this should be fine
        for i in range(len(extra_lines)):
            if extra_lines[i].startswith("output"):
                path = extra_lines[i][9:]

                path = path.replace("_$(Cluster)", "")
                path = path.replace("_$(Process)", "")

                return path
