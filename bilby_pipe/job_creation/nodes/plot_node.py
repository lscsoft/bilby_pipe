from ...utils import logger
from ..node import Node


class PlotNode(Node):
    def __init__(self, inputs, merged_node, dag):
        super().__init__(inputs)
        self.dag = dag
        self.job_name = merged_node.job_name + "_plot"
        self.label = merged_node.job_name + "_plot"
        self.request_cpus = 1
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
