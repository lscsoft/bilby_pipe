import unittest
import shutil

import bilby

from bilby_pipe.main import parse_args
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
            "--data-label",
            "TEST",
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

    def test_set_reference_frequency(self):
        args_list = self.default_args_list + ["--reference-frequency", "10"]
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser), create_data=False
        )
        self.assertEqual(inputs.reference_frequency, 10)

    def test_psd_length_default(self):
        self.assertEqual(32 * self.inputs.duration, self.inputs.psd_duration)

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
        self.assertEqual(
            self.inputs.channel_dict, dict(H1="GDS-CALIB_STRAIN", L1="GDS-CALIB_STRAIN")
        )
        self.assertEqual(self.inputs.label, "label")

    def test_interferometer_unset(self):
        with self.assertRaises(ValueError):
            self.inputs.interferometers

    def test_interferometer_set(self):
        ifos = bilby.gw.detector.InterferometerList(["H1", "L1"])
        self.inputs.interferometers = ifos
        self.assertEqual(ifos, self.inputs.interferometers)

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
        with self.assertRaises(BilbyPipeError):
            self.inputs.detectors = 10

    # def test_trigger_time(self):
    #    args_list = [
    #        "--ini",
    #        "tests/test_data_generation.ini",
    #        "--outdir",
    #        self.outdir,
    #        "--trigger-time",
    #        "1126259462",
    #        "--data-label",
    #        "TEST",
    #    ]
    #    self.inputs = DataGenerationInput(*parse_args(args_list, self.parser))

    def test_injections_no_file(self):
        args_list = [
            "--ini",
            "tests/test_data_generation.ini",
            "--outdir",
            self.outdir,
            "--injection-file",
            "not_a_file",
            "--data-label",
            "TEST",
        ]
        with self.assertRaises(FileNotFoundError):
            self.inputs = DataGenerationInput(*parse_args(args_list, self.parser))


if __name__ == "__main__":
    unittest.main()
