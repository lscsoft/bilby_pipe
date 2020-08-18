from ...utils import DataDump, logger
from ..node import Node


class GenerationNode(Node):
    def __init__(self, inputs, trigger_time, idx, dag, parent=None):
        """
        Node for data generation jobs

        Parameters:
        -----------
        inputs: bilby_pipe.main.MainInput
            The user-defined inputs
        trigger_time: float
            The trigger time to use in generating analysis data
        idx: int
            The index of the data-generation job, used to label data products
        dag: bilby_pipe.dag.Dag
            The dag structure
        parent: bilby_pipe.job_creation.node.Node (optional)
            Any job to set as the parent to this job - used to enforce
            dependencies
        """

        super().__init__(inputs)
        self.inputs = inputs
        self.trigger_time = trigger_time
        self.idx = idx
        self.dag = dag
        self.request_cpus = 1

        self.setup_arguments()
        self.arguments.add("label", self.label)
        self.arguments.add("idx", self.idx)
        self.arguments.add("trigger-time", self.trigger_time)
        if self.inputs.injection_file is not None:
            self.arguments.add("injection-file", self.inputs.injection_file)
        if self.inputs.timeslide_file is not None:
            self.arguments.add("timeslide-file", self.inputs.timeslide_file)
        self.process_node()
        if parent:
            self.job.add_parent(parent.job)

    @property
    def executable(self):
        return self._get_executable_path("bilby_pipe_generation")

    @property
    def request_memory(self):
        return self.inputs.request_memory_generation

    @property
    def log_directory(self):
        return self.inputs.data_generation_log_directory

    @property
    def universe(self):
        if self.inputs.local_generation:
            logger.debug(
                "Data generation done locally: please do not use this when "
                "submitting a large number of jobs"
            )
            universe = "local"
        else:
            logger.debug(
                "All data will be grabbed in the {} universe".format(self._universe)
            )
            universe = self._universe
        return universe

    @property
    def job_name(self):
        job_name = "{}_data{}_{}_generation".format(
            self.inputs.label, str(self.idx), self.trigger_time
        )
        job_name = job_name.replace(".", "-")
        return job_name

    @property
    def label(self):
        return self.job_name

    @property
    def data_dump_file(self):
        return DataDump.get_filename(self.inputs.data_directory, self.label)
