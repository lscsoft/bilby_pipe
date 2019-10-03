import os
import unittest

import bilby

import bilby_pipe
from bilby_pipe.utils import BilbyPipeError


class TestInput(unittest.TestCase):
    def setUp(self):
        self.test_gps_file = "tests/gps_file.txt"

    def tearDown(self):
        pass

    def test_idx(self):
        inputs = bilby_pipe.main.Input()
        inputs.idx = 1
        self.assertEqual(inputs.idx, 1)

    def test_split_by_space(self):
        inputs = bilby_pipe.main.Input()
        out = inputs._split_string_by_space("H1 L1")
        self.assertEqual(out, ["H1", "L1"])

    def test_known_detectors(self):
        inputs = bilby_pipe.main.Input()
        self.assertEqual(inputs.known_detectors, ["H1", "L1", "V1"])

    def test_set_known_detectors_list(self):
        inputs = bilby_pipe.main.Input()
        inputs.known_detectors = ["G1"]
        self.assertEqual(inputs.known_detectors, ["G1"])

    def test_set_known_detectors_string(self):
        inputs = bilby_pipe.main.Input()
        inputs.known_detectors = "G1 H1"
        self.assertEqual(inputs.known_detectors, ["G1", "H1"])

    def test_detectors(self):
        inputs = bilby_pipe.main.Input()
        with self.assertRaises(AttributeError):
            print(inputs.detectors)

    def test_set_detectors_list(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = ["H1"]
        self.assertEqual(inputs.detectors, ["H1"])

    def test_set_detectors_string(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = "H1 L1"
        self.assertEqual(inputs.detectors, ["H1", "L1"])

    def test_set_detectors_ordering(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = "L1 H1"
        self.assertEqual(inputs.detectors, ["H1", "L1"])

    def test_unknown_detector(self):
        inputs = bilby_pipe.main.Input()
        with self.assertRaises(BilbyPipeError):
            inputs.detectors = "G1"

        with self.assertRaises(BilbyPipeError):
            inputs.detectors = ["G1", "L1"]

        inputs.known_detectors = inputs.known_detectors + ["G1"]
        inputs.detectors = ["G1", "L1"]
        self.assertEqual(inputs.detectors, ["G1", "L1"])

    def test_convert_string_to_list(self):
        for string in [
            "H1 L1",
            "[H1, L1]",
            "H1, L1",
            '["H1", "L1"]',
            "'H1' 'L1'",
            '"H1", "L1"',
        ]:
            self.assertEqual(
                bilby_pipe.main.Input._convert_string_to_list(string), ["H1", "L1"]
            )

    def test_gps_file_unset(self):
        inputs = bilby_pipe.main.Input()
        with self.assertRaises(AttributeError):
            self.assertEqual(inputs.gps_file, None)

    def test_gps_file_set_none(self):
        inputs = bilby_pipe.main.Input()
        inputs.gps_file = None
        self.assertEqual(inputs.gps_file, None)

    def test_gps_file_set(self):
        inputs = bilby_pipe.main.Input()
        inputs.gps_file = self.test_gps_file
        self.assertEqual(inputs.gps_file, os.path.relpath(self.test_gps_file))
        self.assertEqual(len(inputs.read_gps_file()), 2)

    def test_gps_file_set_fail(self):
        inputs = bilby_pipe.main.Input()
        gps_file = "tests/nonexistant_file.txt"
        with self.assertRaises(FileNotFoundError):
            inputs.gps_file = gps_file

    def test_frequency_domain_source_model(self):
        inputs = bilby_pipe.main.Input()
        inputs.frequency_domain_source_model = "lal_binary_black_hole"
        self.assertEqual(inputs.frequency_domain_source_model, "lal_binary_black_hole")

    def test_frequency_domain_source_model_to_bilby(self):
        inputs = bilby_pipe.main.Input()
        inputs.frequency_domain_source_model = "lal_binary_black_hole"
        self.assertEqual(
            inputs.bilby_frequency_domain_source_model,
            bilby.gw.source.lal_binary_black_hole,
        )

    def test_frequency_domain_source_model_to_bilby_fail(self):
        inputs = bilby_pipe.main.Input()
        inputs.frequency_domain_source_model = "not_a_source_model"
        with self.assertRaises(BilbyPipeError):
            print(inputs.bilby_frequency_domain_source_model)

    def test_minimum_frequency_int(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = "H1 L1"
        inputs.minimum_frequency = 10
        self.assertEqual(inputs.minimum_frequency, 10)
        self.assertEqual(inputs.minimum_frequency_dict, dict(H1=10, L1=10))

    def test_minimum_frequency_float(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = "H1 L1"
        inputs.minimum_frequency = 10.1
        self.assertEqual(inputs.minimum_frequency, 10.1)
        self.assertEqual(inputs.minimum_frequency_dict, dict(H1=10.1, L1=10.1))

    def test_minimum_frequency_int_dict(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = "H1 L1"
        inputs.minimum_frequency = "{H1: 10, L1: 20}"
        self.assertIsInstance(inputs.minimum_frequency, int)
        self.assertEqual(inputs.minimum_frequency, 10)
        self.assertEqual(inputs.minimum_frequency_dict, dict(H1=10, L1=20))

    def test_minimum_frequency_float_dict(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = "H1 L1"
        inputs.minimum_frequency = "{H1: 10.1, L1: 20.1}"
        self.assertIsInstance(inputs.minimum_frequency, float)
        self.assertEqual(inputs.minimum_frequency, 10.1)
        self.assertEqual(inputs.minimum_frequency_dict, dict(H1=10.1, L1=20.1))

    def test_maximum_frequency_int(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = "H1 L1"
        inputs.maximum_frequency = 10
        self.assertEqual(inputs.maximum_frequency, 10)
        self.assertEqual(inputs.maximum_frequency_dict, dict(H1=10, L1=10))

    def test_maximum_frequency_str(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = "H1 L1"
        inputs.maximum_frequency = "10"
        self.assertEqual(inputs.maximum_frequency, 10)
        self.assertEqual(inputs.maximum_frequency_dict, dict(H1=10, L1=10))

    def test_maximum_frequency_float(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = "H1 L1"
        inputs.maximum_frequency = 10.1
        self.assertEqual(inputs.maximum_frequency, 10.1)
        self.assertEqual(inputs.maximum_frequency_dict, dict(H1=10.1, L1=10.1))

    def test_maximum_frequency_int_dict(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = "H1 L1"
        inputs.maximum_frequency = "{H1: 100, L1: 200}"
        self.assertIsInstance(inputs.maximum_frequency, int)
        self.assertEqual(inputs.maximum_frequency, 200)
        self.assertEqual(inputs.maximum_frequency_dict, dict(H1=100, L1=200))

    def test_maximum_frequency_float_dict(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = "H1 L1"
        inputs.maximum_frequency = "{H1: 100.1, L1: 200.1}"
        self.assertIsInstance(inputs.maximum_frequency, float)
        self.assertEqual(inputs.maximum_frequency, 200.1)
        self.assertEqual(inputs.maximum_frequency_dict, dict(H1=100.1, L1=200.1))

    def test_default_webdir(self):
        inputs = bilby_pipe.main.Input()
        inputs.outdir = "results"
        inputs.webdir = None
        self.assertEqual(inputs.webdir, "results/results_page")

    def test_default_start_time(self):
        inputs = bilby_pipe.main.Input()
        inputs.trigger_time = 2
        inputs.post_trigger_duration = 2
        inputs.duration = 4
        self.assertEqual(inputs.start_time, 0)

    def test_set_start_time(self):
        inputs = bilby_pipe.main.Input()
        inputs.start_time = 2
        self.assertEqual(inputs.start_time, 2)

    def test_set_start_time_fail(self):
        inputs = bilby_pipe.main.Input()
        inputs.trigger_time = 2
        inputs.duration = 4
        inputs.post_trigger_duration = 2
        with self.assertRaises(BilbyPipeError):
            inputs.start_time = 2

    def test_default_waveform_arguments(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = ["H1"]
        inputs.reference_frequency = 20
        inputs.minimum_frequency = 20
        inputs.waveform_approximant = "IMRPhenomPv2"
        wfa = inputs.get_default_waveform_arguments()
        self.assertEqual(wfa["reference_frequency"], 20)
        self.assertEqual(wfa["minimum_frequency"], 20)
        self.assertEqual(wfa["waveform_approximant"], "IMRPhenomPv2")
        self.assertEqual(len(wfa), 3)

    def test_bilby_roq_frequency_domain_source_model(self):
        inputs = bilby_pipe.main.Input()
        inputs.frequency_domain_source_model = "lal_binary_black_hole"
        self.assertEqual(
            inputs.bilby_roq_frequency_domain_source_model,
            bilby.gw.source.binary_black_hole_roq,
        )

        inputs.frequency_domain_source_model = "lal_binary_neutron_star"
        self.assertEqual(
            inputs.bilby_roq_frequency_domain_source_model,
            bilby.gw.source.binary_neutron_star_roq,
        )

        with self.assertRaises(BilbyPipeError):
            inputs.frequency_domain_source_model = "unknown"
            inputs.bilby_roq_frequency_domain_source_model


if __name__ == "__main__":
    unittest.main()
