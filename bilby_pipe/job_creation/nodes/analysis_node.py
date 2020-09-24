import os

from ..node import Node


class AnalysisNode(Node):
    def __init__(self, inputs, generation_node, detectors, sampler, parallel_idx, dag):
        super().__init__(inputs)
        self.dag = dag
        self.generation_node = generation_node
        self.detectors = detectors
        self.parallel_idx = parallel_idx
        self.request_cpus = inputs.request_cpus

        data_label = generation_node.job_name
        base_name = data_label.replace("generation", "analysis")
        self.base_job_name = f"{base_name}_{''.join(detectors)}_{sampler}"
        if parallel_idx != "":
            self.job_name = f"{self.base_job_name}_{parallel_idx}"
        else:
            self.job_name = self.base_job_name
        self.label = self.job_name

        if self.inputs.use_mpi:
            self.setup_arguments(
                parallel_program=self._get_executable_path("bilby_pipe_analysis")
            )

        else:
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
            self.arguments.add("outdir", os.path.relpath(self.inputs.outdir))

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
        if self.inputs.use_mpi:
            return self._get_executable_path("mpiexec")

        return self._get_executable_path("bilby_pipe_analysis")

    @property
    def request_memory(self):
        return self.inputs.request_memory

    @property
    def log_directory(self):
        return self.inputs.data_analysis_log_directory

    @property
    def result_file(self):
        return f"{self.inputs.result_directory}/{self.job_name}_result.json"

    @property
    def slurm_walltime(self):
        """ Default wall-time for base-name """
        # Seven days
        return self.inputs.scheduler_analysis_time
