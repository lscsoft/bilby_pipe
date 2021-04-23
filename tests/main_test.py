import copy
import os
import shutil
import unittest

import numpy as np

import bilby_pipe
from bilby_pipe.utils import BilbyPipeError


class TestMainInput(unittest.TestCase):
    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.outdir = "outdir"
        self.known_args_list = [
            "tests/test_main_input.ini",
            "--submit",
            "--outdir",
            self.outdir,
        ]
        self.unknown_args_list = ["--argument", "value"]
        self.all_args_list = self.known_args_list + self.unknown_args_list
        self.parser = bilby_pipe.main.create_parser()
        self.args = self.parser.parse_args(self.known_args_list)
        self.inputs = bilby_pipe.main.MainInput(
            *self.parser.parse_known_args(self.all_args_list)
        )

        self.test_gps_file = "tests/gps_file.txt"

    def tearDown(self):
        shutil.rmtree(self.outdir)
        del self.args
        del self.inputs

    def test_ini(self):
        self.assertEqual(self.inputs.ini, os.path.relpath(self.args.ini))

    def test_initialdir(self):
        self.assertEqual(self.inputs.initialdir, os.getcwd())

    def test_ini_not_a_file(self):
        with self.assertRaises(FileNotFoundError):
            self.inputs.ini = "not_a_file"

    def test_submit(self):
        self.assertEqual(self.inputs.submit, self.args.submit)

    def test_request_cpus(self):
        self.assertEqual(self.inputs.request_cpus, self.args.request_cpus)

    def test_request_memory(self):
        memory = f"{self.args.request_memory} GB"
        self.assertEqual(self.inputs.request_memory, memory)

    def test_request_memory_generation_default_non_roq(self):
        mem_int = bilby_pipe.utils.request_memory_generation_lookup(
            self.args.duration, roq=False
        )
        memory = f"{mem_int} GB"
        self.assertEqual(self.inputs.request_memory_generation, memory)

    def test_request_memory_generation_default_roq(self):
        self.inputs.likelihood_type = "ROQGravitationalWaveTransient"
        mem_int = bilby_pipe.utils.request_memory_generation_lookup(
            self.args.duration, roq=True
        )
        memory = f"{mem_int} GB"
        self.assertEqual(self.inputs.request_memory_generation, memory)

    def test_request_memory_generation_set(self):
        self.args.request_memory_generation = 4
        inputs = bilby_pipe.main.MainInput(self.args, [])
        memory = f"{self.args.request_memory_generation} GB"
        self.assertEqual(inputs.request_memory_generation, memory)

    def test_notification_set(self):
        self.args.notification = "Always"
        inputs = bilby_pipe.main.MainInput(self.args, [])
        self.assertEqual(inputs.notification, "Always")

    def test_notification_error_riased_set(self):
        self.args.notification = "Sometimes"
        with self.assertRaises(BilbyPipeError):
            bilby_pipe.main.MainInput(self.args, [])

    def test_label(self):
        self.assertEqual(self.inputs.label, self.args.label)

    def test_coherence_test(self):
        self.assertEqual(self.inputs.coherence_test, self.args.coherence_test)

    def test_accounting(self):
        self.assertEqual(self.inputs.accounting, self.args.accounting)

    def test_result_format(self):
        self.assertEqual(self.inputs.result_format, self.args.result_format)

    def test_detectors_single(self):
        # Test the detector set in the ini file
        self.assertEqual(self.inputs.detectors, ["H1"])

        # Test setting a single detector directly in the args as a string
        args = copy.copy(self.args)
        args.detectors = "L1"
        inputs = bilby_pipe.main.MainInput(args, [])
        self.assertEqual(inputs.detectors, ["L1"])

        args.detectors = ["L1"]
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.detectors, ["L1"])

        with self.assertRaises(BilbyPipeError):
            args.detectors = None
            inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)

    def test_detectors_multiple(self):
        args = copy.copy(self.args)
        args.detectors = "H1 L1"
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.detectors, ["H1", "L1"])

        args.detectors = "L1 H1"
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.detectors, ["H1", "L1"])

        args.detectors = ["L1 H1"]
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.detectors, ["H1", "L1"])

        args.detectors = ["L1", "H1"]
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.detectors, ["H1", "L1"])

        args.detectors = ["H1", "L1"]
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.detectors, ["H1", "L1"])

        args.detectors = ["H1", "l1"]
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)

    def test_create_summary_page(self):
        self.assertEqual(self.inputs.create_summary, self.args.create_summary)
        self.assertEqual(self.inputs.email, self.args.email)
        self.assertEqual(self.inputs.webdir, self.args.webdir)
        self.assertEqual(self.inputs.existing_dir, self.args.existing_dir)

    def test_n_simulation_setting(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        inputs.n_simulation = 1
        self.assertEqual(inputs.n_simulation, 1)

        inputs.n_simulation = 3
        self.assertEqual(inputs.n_simulation, 3)

    # def test_n_simulation_None(self):
    #    args = self.args
    #    args.injection = True
    #    args.n_simulation = None
    #    inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
    #    self.assertEqual(inputs.n_simulation, 0)

    def test_get_trigger_time_list(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)

        inputs.trigger_time = 10
        self.assertEqual(
            bilby_pipe.job_creation.bilby_pipe_dag_creator.get_trigger_time_list(
                inputs
            ),
            [10],
        )

    def test_get_trigger_time_list_gps_file(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)

        inputs.gps_file = self.test_gps_file
        A = bilby_pipe.job_creation.bilby_pipe_dag_creator.get_trigger_time_list(inputs)
        start_times = np.genfromtxt(self.test_gps_file)
        B = start_times + inputs.duration - inputs.post_trigger_duration
        self.assertTrue(np.all(A == B))

    def test_get_trigger_time_list_with_gaussian_noise_and_trigger_time(self):
        args = self.args
        args.trigger_time = 10
        args.gaussian_noise = True
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)

        self.assertEqual(
            bilby_pipe.job_creation.bilby_pipe_dag_creator.get_trigger_time_list(
                inputs
            ),
            [args.trigger_time],
        )

    def test_get_trigger_time_list_gaussian_noise(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)

        inputs.gaussian_noise = True
        inputs.n_simulation = 3
        t = 0 + inputs.duration - inputs.post_trigger_duration
        self.assertTrue(
            bilby_pipe.job_creation.bilby_pipe_dag_creator.get_trigger_time_list(
                inputs
            ),
            [t] * 3,
        )

    def test_get_trigger_time_list_fail(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)

        with self.assertRaises(BilbyPipeError):
            bilby_pipe.job_creation.bilby_pipe_dag_creator.get_trigger_time_list(inputs)

    def test_get_detectors_list(self):
        self.args.detectors = ["H1", "L1", "V1"]
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        det_list = bilby_pipe.job_creation.bilby_pipe_dag_creator.get_detectors_list(
            inputs
        )
        self.assertTrue(det_list, [["H1", "L1", "V1"]])

        self.args.detectors = ["H1", "L1", "V1"]
        self.args.coherence_test = True
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        det_list = bilby_pipe.job_creation.bilby_pipe_dag_creator.get_detectors_list(
            inputs
        )
        self.assertTrue(det_list, [["H1", "L1", "V1"], ["H1"], ["L1"], ["V1"]])


if __name__ == "__main__":
    unittest.main()
