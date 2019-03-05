import unittest
import shutil
import os
from argparse import Namespace
import json

import bilby

from bilby_pipe.main import parse_args
from bilby_pipe import create_injections
from bilby_pipe.data_generation import DataGenerationInput, create_generation_parser
from bilby_pipe.utils import BilbyPipeError


class TestDataGenerationInput(unittest.TestCase):
    def setUp(self):
        self.outdir = "test_outdir"
        self.default_args_list = [
            "--ini",
            "tests/test_data_generation.ini",
            "--outdir",
            self.outdir,
        ]
        self.parser = create_generation_parser()
        self.inputs = DataGenerationInput(
            *parse_args(self.default_args_list, self.parser), create_data=False
        )
        self.gps_file = "tests/gps_file.txt"

    def tearDown(self):
        del self.default_args_list
        del self.parser
        del self.inputs
        shutil.rmtree(self.outdir)

    def test_cluster_set(self):
        self.inputs.cluster = 123
        self.assertEqual(123, self.inputs.cluster)

    def test_process_set(self):
        self.inputs.process = 321
        self.assertEqual(321, self.inputs.process)

    def test_parameter_conversion(self):
        self.inputs.frequency_domain_source_model = "binary_neutron_star"
        self.assertEqual(
            self.inputs.parameter_conversion,
            bilby.gw.conversion.convert_to_lal_binary_neutron_star_parameters,
        )
        self.inputs.frequency_domain_source_model = "binary_black_hole"
        self.assertEqual(
            self.inputs.parameter_conversion,
            bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters,
        )

    def test_psd_length_set(self):
        self.inputs.psd_length = 10
        self.assertEqual(10, self.inputs.psd_length)
        self.assertEqual(
            10 * self.inputs.duration, self.inputs.psd_length * self.inputs.duration
        )

    def test_psd_length_default(self):
        self.inputs.duration = 4
        self.assertEqual(32 * 4, self.inputs.psd_duration)

    def test_psd_start_time_set(self):
        self.inputs.psd_start_time = 10
        self.assertEqual(10, self.inputs.psd_start_time)

    def test_psd_start_time_default(self):
        self.inputs.psd_duration = 4
        self.inputs.trigger_time = 12
        self.assertEqual(-4, self.inputs.psd_start_time)

    def test_psd_start_time_fail(self):
        self.inputs.psd_duration = 4
        self.inputs.start_time = 10
        self.inputs.trigger_time = None
        self.inputs.psd_start_time = None
        with self.assertRaises(BilbyPipeError):
            self.assertEqual(10 - 4, self.inputs.psd_start_time)

    def test_script_inputs_from_test_ini(self):
        self.assertEqual(self.inputs.channel_type, ["GDS-CALIB_STRAIN"])
        self.assertEqual(self.inputs.label, "label")

    def test_interferometer_unset(self):
        with self.assertRaises(ValueError):
            self.inputs.interferometers

    def test_interferometer_set(self):
        self.inputs.interferometers = ["a", "b"]
        self.assertEqual(["a", "b"], self.inputs.interferometers)

    def test_script_inputs_detectors_from_ini(self):
        self.assertEqual(self.inputs.detectors, ["H1", "L1"])

    def test_script_inputs_detectors_from_command_line(self):
        args_list = self.default_args_list + ["--detectors", "H1", "--detectors", "L1"]
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser), create_data=False
        )
        self.assertEqual(inputs.detectors, ["H1", "L1"])

        args_list = self.default_args_list + ["--detectors", "H1 L1"]
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser), create_data=False
        )
        self.assertEqual(inputs.detectors, ["H1", "L1"])

        args_list = self.default_args_list + ["--detectors", "L1 H1"]
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser), create_data=False
        )
        self.assertEqual(inputs.detectors, ["H1", "L1"])

        args_list = self.default_args_list + ["--detectors", "[L1, H1]"]
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser), create_data=False
        )

        args_list = self.default_args_list + ["--detectors", "[L1 H1]"]
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser), create_data=False
        )
        self.assertEqual(inputs.detectors, ["H1", "L1"])

        args_list = self.default_args_list + ["--detectors", '["L1", "H1"]']
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser), create_data=False
        )
        self.assertEqual(inputs.detectors, ["H1", "L1"])

        args_list = self.default_args_list + ["--detectors", "['L1', 'H1']"]
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser), create_data=False
        )
        self.assertEqual(inputs.detectors, ["H1", "L1"])

    def test_detectors_not_understood(self):
        with self.assertRaises(ValueError):
            self.inputs.detectors = 10

    def test_minimum_frequency(self):
        self.inputs.minimum_frequency = 10
        self.assertEqual(self.inputs.minimum_frequency, 10)

    # def test_set_gracedb_fail(self):
    #     with self.assertRaises(BilbyPipeError):
    #         self.inputs.gracedb = "NOT-A-GRACEDB"

    def test_trigger_time(self):
        args_list = [
            "--ini",
            "tests/test_data_generation.ini",
            "--outdir",
            self.outdir,
            "--trigger-time",
            "1126259462",
        ]
        self.inputs = DataGenerationInput(*parse_args(args_list, self.parser))

    def test_gps_file(self):
        args_list = [
            "--ini",
            "tests/test_data_generation.ini",
            "--outdir",
            self.outdir,
            "--gps-file",
            self.gps_file,
            "--idx" "0",
        ]
        self.inputs = DataGenerationInput(*parse_args(args_list, self.parser))

    def test_injections_no_file(self):
        args_list = [
            "--ini",
            "tests/test_data_generation.ini",
            "--outdir",
            self.outdir,
            "--injection-file",
            "not_a_file",
        ]
        with self.assertRaises(FileNotFoundError):
            self.inputs = DataGenerationInput(*parse_args(args_list, self.parser))

    def test_injections(self):
        inj_args = Namespace(
            prior_file="tests/example_prior.prior",
            n_injection=3,
            outdir=self.outdir,
            label="label",
            generation_seed=None,
        )
        inj_inputs = create_injections.CreateInjectionInput(inj_args, [])
        injection_file_name = os.path.join(self.outdir, "injection_file.h5")
        inj_inputs.create_injection_file(injection_file_name)

        args_list = [
            "--ini",
            "tests/test_data_generation.ini",
            "--outdir",
            self.outdir,
            "--injection-file",
            injection_file_name,
        ]
        self.inputs = DataGenerationInput(*parse_args(args_list, self.parser))

        # Check the injections match by idx
        with open(injection_file_name, "r") as file:
            injection_file_dict = json.load(
                file, object_hook=bilby.core.result.decode_bilby_json_result
            )
        self.assertEqual(
            self.inputs.meta_data["injection_parameters"],
            injection_file_dict["injections"].iloc[self.inputs.idx].to_dict(),
        )

        self.inputs.save_interferometer_list()
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    self.outdir,
                    "data",
                    "{}_{}_data_dump.pickle".format(self.inputs.label, self.inputs.idx),
                )
            )
        )

        self.assertEqual(
            self.inputs.injection_file, os.path.abspath(injection_file_name)
        )


if __name__ == "__main__":
    unittest.main()
