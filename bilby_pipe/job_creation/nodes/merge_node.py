from ..node import Node


class MergeNode(Node):
    def __init__(self, inputs, parallel_node_list, detectors, dag):
        super().__init__(inputs)
        self.dag = dag

        self.job_name = f"{parallel_node_list[0].base_job_name}_merge"
        self.label = f"{parallel_node_list[0].base_job_name}_merge"
        self.request_cpus = 1
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
        return f"{self.inputs.result_directory}/{self.label}_result.json"
