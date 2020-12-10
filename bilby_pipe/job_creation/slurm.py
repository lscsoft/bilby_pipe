#!/usr/bin/env python
"""
Module containing the tools for outputting slurm submission scripts
"""

import os
import subprocess

from ..utils import logger


class SubmitSLURM(object):
    def __init__(self, dag):

        self.dag = dag.pycondor_dag
        self.submit_dir = dag.inputs.submit_directory
        self.submit = dag.inputs.submit
        self.label = dag.inputs.label
        self.scheduler = dag.scheduler
        self.scheduler_args = dag.scheduler_args
        self.scheduler_module = dag.scheduler_module
        self.scheduler_env = dag.scheduler_env
        self.scheduler_analysis_time = dag.scheduler_analysis_time

    def run_local_generation(self):
        for node in self.dag.nodes:
            if "_generation" in node.name:
                # Run the job locally
                cmd = " ".join([node.executable, node.args[0].arg])
                subprocess.run(cmd, shell=True)
                # Remove the children
                for other_node in self.dag.nodes:
                    if node in other_node.parents:
                        other_node.parents.remove(node)
                self.dag.nodes.remove(node)

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

            f.write("#!/bin/bash\n")

            for arg in slurm_args.split():
                f.write(f"#SBATCH {arg}\n")

            f.write("#SBATCH --time=00:10:00\n")

            # write output to standard file
            f.write(
                f"#SBATCH --output={self.submit_dir}/{self.label}_master_slurm.out\n"
            )
            f.write(
                f"#SBATCH --error={self.submit_dir}/{self.label}_master_slurm.err\n"
            )

            if self.scheduler_module:
                for module in self.scheduler_module:
                    if module is not None:
                        f.write(f"\nmodule load {module}\n")

            # if self.scheduler_env is not None:
            #    f.write("\nsource {}\n".format(self.scheduler_env))

            # assign new job ID to each process
            jids = range(len(self.dag.nodes))

            job_names = [node.name for node in self.dag.nodes]

            # create dict for assigning ID to job name
            job_dict = dict(zip(job_names, jids))

            for node, indx in zip(self.dag.nodes, jids):
                # Generate the real slurm arguments from the dag node and the parsed slurm args
                job_slurm_args = slurm_args
                job_slurm_args += " --nodes=1"
                job_slurm_args += f" --ntasks-per-node={node.request_cpus}"
                job_slurm_args += " --mem={}G".format(
                    int(float(node.request_memory.split(" ")[0]))
                )
                job_slurm_args += f" --time={node.slurm_walltime}"
                job_slurm_args += f" --job-name={node.name}"

                submit_str = f"\njid{indx}=($(sbatch {job_slurm_args} "

                # get list of all parents associated with job
                parents = [job.name for job in node.parents]

                if len(parents) > 0:
                    # only run subsequent jobs after parent has
                    # *successfully* completed
                    submit_str += "--dependency=afterok"

                    for parent in parents:
                        submit_str += f":${{jid{job_dict[parent]}[-1]}}"
                # get output file path from dag and use for slurm
                output_file = self._output_name_from_dag(node.extra_lines)

                submit_str += f" --output={output_file}"
                submit_str += f" --error={output_file.replace('.out', '.err')}"

                job_script = self._write_individual_processes(
                    node.name, node.executable, node.args[0].arg
                )

                submit_str += f" {job_script}))\n\n"
                submit_str += (
                    f'echo "jid{indx} ${{jid{indx}[-1]}}" >> {self.slurm_id_file}'
                )

                f.write(f"{submit_str}\n")

        # print out how to submit
        command_line = f"sbatch {self.slurm_master_bash}"

        if self.submit:
            subprocess.run([command_line], shell=True)
        else:
            logger.info(f"slurm scripts written, to run jobs submit:\n$ {command_line}")

    def _write_individual_processes(self, name, executable, args):

        fname = name + ".sh"
        job_path = self.submit_dir + "/" + fname

        with open(job_path, "w") as ff:

            ff.write("#!/bin/bash\n")

            if self.scheduler_module:
                for module in self.scheduler_module:
                    if module is not None:
                        ff.write(f"\nmodule load {module}\n")

            if self.scheduler_env is not None:
                ff.write(f"\nsource {self.scheduler_env}\n\n")
                # Call python from the venv on the script directly to avoid
                # "bad interpreter" from shebang exceeding 128 chars
                job_str = f"python {executable} {args}\n\n"
            else:
                job_str = f"{executable} {args}\n\n"

            ff.write(job_str)

        return job_path

    @property
    def slurm_master_bash(self):
        """
        Create filename for master script
        """
        filebasename = "_".join(["slurm", self.label, "master.sh"])
        return os.path.join(self.submit_dir, filebasename)

    @property
    def slurm_id_file(self):
        """
        Create the file that should store the slurm ids of the jobs
        """
        return os.path.join(self.submit_dir, "slurm_ids")

    @staticmethod
    def _output_name_from_dag(extra_lines):

        # probably a faster way to do this, but the list is short so this should be fine
        for i in range(len(extra_lines)):
            if extra_lines[i].startswith("output"):
                path = extra_lines[i][9:]

                path = path.replace("_$(Cluster)", "")
                path = path.replace("_$(Process)", "")

                return path
