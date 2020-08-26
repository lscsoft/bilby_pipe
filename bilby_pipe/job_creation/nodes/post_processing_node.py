from ..node import Node


class PostProcessSingleResultsNode(Node):
    def __init__(self, inputs, merged_node, dag):
        super().__init__(inputs)
        self.dag = dag
        self.request_cpus = 1
        self.job_name = f"{merged_node.label}_postprocess_single"

        self.setup_arguments(
            add_ini=False, add_unknown_args=False, add_command_line_args=False
        )

        alist = self.inputs.single_postprocessing_arguments.split()
        alist = [arg.replace("$RESULT", merged_node.result_file) for arg in alist]
        self.arguments.argument_list = alist
        self.process_node()
        self.job.add_parent(merged_node.job)

    @property
    def executable(self):
        return self._get_executable_path(self.inputs.single_postprocessing_executable)

    @property
    def request_memory(self):
        return "4 GB"

    @property
    def log_directory(self):
        return self.inputs.data_analysis_log_directory


class PostProcessAllResultsNode(Node):
    def __init__(self, inputs, merged_node_list, dag):
        super().__init__(inputs)
        self.dag = dag
        self.request_cpus = 1
        self.job_name = f"{self.inputs.label}_postprocess_all"
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
