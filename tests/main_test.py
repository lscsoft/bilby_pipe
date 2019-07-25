import os
import unittest
import copy
import shutil

import bilby_pipe
from bilby_pipe.main import BilbyPipeError


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
        self.singularity_image_test = os.path.join(self.outdir, "test.simg")
        with open(self.singularity_image_test, "w+") as file:
            file.write("")

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

    def test_set_singularity_image(self):
        self.inputs.singularity_image = self.singularity_image_test
        self.assertEqual(
            self.inputs.singularity_image, os.path.abspath(self.singularity_image_test)
        )

    def test_singularity_image_setting_fail(self):
        with self.assertRaises(BilbyPipeError):
            self.inputs.singularity_image = 10

        with self.assertRaises(FileNotFoundError):
            self.inputs.singularity_image = "not_a_file"

    def test_use_singularity(self):
        self.inputs.use_singularity = True
        self.assertEqual(self.inputs.use_singularity, True)

        with self.assertRaises(BilbyPipeError):
            self.inputs.use_singularity = 10

    def test_setting_level_A_jobs(self):
        self.inputs.n_level_A_jobs = 10
        self.assertEqual(self.inputs.n_level_A_jobs, 10)

    def test_setting_level_A_labels(self):
        self.inputs.level_A_labels = ["a", "b"]
        self.assertEqual(self.inputs.level_A_labels, ["a", "b"])

    def test_submit(self):
        self.assertEqual(self.inputs.submit, self.args.submit)

    def test_request_cpus(self):
        self.assertEqual(self.inputs.request_cpus, self.args.request_cpus)

    def test_request_memory(self):
        memory = "{} GB".format(self.args.request_memory)
        self.assertEqual(self.inputs.request_memory, memory)

    def test_request_memory_generation_default_non_roq(self):
        mem_int = bilby_pipe.utils.request_memory_generation_lookup(
            self.args.duration, roq=False
        )
        memory = "{} GB".format(mem_int)
        self.assertEqual(self.inputs.request_memory_generation, memory)

    def test_request_memory_generation_default_roq(self):
        self.inputs.likelihood_type = "ROQGravitationalWaveTransient"
        mem_int = bilby_pipe.utils.request_memory_generation_lookup(
            self.args.duration, roq=True
        )
        memory = "{} GB".format(mem_int)
        self.assertEqual(self.inputs.request_memory_generation, memory)

    def test_request_memory_generation_set(self):
        self.args.request_memory_generation = 4
        inputs = bilby_pipe.main.MainInput(self.args, [])
        memory = "{} GB".format(self.args.request_memory_generation)
        self.assertEqual(inputs.request_memory_generation, memory)

    def test_label(self):
        self.assertEqual(self.inputs.label, self.args.label)

    def test_coherence_test(self):
        self.assertEqual(self.inputs.coherence_test, self.args.coherence_test)

    def test_accounting(self):
        self.assertEqual(self.inputs.accounting, self.args.accounting)

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
            args.detectors = "A1"
            inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)

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

        with self.assertRaises(BilbyPipeError):
            args.detectors = ["H1", "error"]
            inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)

    def test_create_summary_page(self):
        self.assertEqual(self.inputs.create_summary, self.args.create_summary)
        self.assertEqual(self.inputs.email, self.args.email)
        self.assertEqual(self.inputs.webdir, self.args.webdir)
        self.assertEqual(self.inputs.existing_dir, self.args.existing_dir)

    def test_parse_gps_file(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        inputs.gps_file = self.test_gps_file
        inputs._parse_gps_file()
        self.assertEqual(len(inputs.read_gps_file()), inputs.n_level_A_jobs)
        self.assertEqual(inputs.level_A_labels, ["1126259462.0", "1126259466.0"])

    def test_n_injection_setting(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        inputs.n_injection = 1
        self.assertEqual(inputs.n_injection, 1)
        self.assertEqual(inputs.n_level_A_jobs, 1)
        self.assertEqual(inputs.level_A_labels, ["injection0"])

    def test_n_injection_and_gpstime_fail(self):
        args = self.args
        args.injection = True
        args.n_injection = 1
        args.gps_file = self.test_gps_file
        with self.assertRaises(BilbyPipeError):
            bilby_pipe.main.MainInput(self.args, self.unknown_args_list)

    def test_n_injection_setting_into_gpstimes(self):
        args = self.args
        args.injection = True
        args.n_injection = None
        args.gps_file = self.test_gps_file
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        self.assertEqual(inputs.n_injection, 2)
        self.assertEqual(inputs.n_level_A_jobs, 2)
        self.assertEqual(
            inputs.level_A_labels,
            ["1126259462.0_injection0", "1126259466.0_injection1"],
        )

    def test_n_injection_None(self):
        args = self.args
        args.injection = True
        args.n_injection = None
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        self.assertEqual(inputs.n_injection, None)


if __name__ == "__main__":
    unittest.main()
