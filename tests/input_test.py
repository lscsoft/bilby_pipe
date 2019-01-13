import os
import unittest

import bilby

import bilby_pipe
from bilby_pipe.utils import BilbyPipeError


class TestInput(unittest.TestCase):
    def setUp(self):
        self.test_gps_file = 'tests/gps_file.txt'

    def tearDown(self):
        pass

    def test_idx(self):
        inputs = bilby_pipe.main.Input()
        inputs.idx = 1
        self.assertEqual(inputs.idx, 1)

    def test_known_detectors(self):
        inputs = bilby_pipe.main.Input()
        self.assertEqual(inputs.known_detectors, ['H1', 'L1', 'V1'])

    def test_set_known_detectors_list(self):
        inputs = bilby_pipe.main.Input()
        inputs.known_detectors = ['G1']
        self.assertEqual(inputs.known_detectors, ['G1'])

    def test_set_known_detectors_string(self):
        inputs = bilby_pipe.main.Input()
        inputs.known_detectors = 'G1 H1'
        self.assertEqual(inputs.known_detectors, ['G1', 'H1'])

    def test_detectors(self):
        inputs = bilby_pipe.main.Input()
        with self.assertRaises(AttributeError):
            inputs.detectors

    def test_set_detectors_list(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = ['H1']
        self.assertEqual(inputs.detectors, ['H1'])

    def test_set_detectors_string(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = 'H1 L1'
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    def test_set_detectors_ordering(self):
        inputs = bilby_pipe.main.Input()
        inputs.detectors = 'L1 H1'
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    def test_unknown_detector(self):
        inputs = bilby_pipe.main.Input()
        with self.assertRaises(BilbyPipeError):
            inputs.detectors = 'G1'

        with self.assertRaises(BilbyPipeError):
            inputs.detectors = ['G1', 'L1']

        inputs.known_detectors = inputs.known_detectors + ['G1']
        inputs.detectors = ['G1', 'L1']
        self.assertEqual(inputs.detectors, ['G1', 'L1'])

    def test_convert_string_to_list(self):
        for string in ['H1 L1', '[H1, L1]', 'H1, L1', '["H1", "L1"]',
                       "'H1' 'L1'", '"H1", "L1"']:
            self.assertEqual(bilby_pipe.main.Input._convert_string_to_list(string),
                             ['H1', 'L1'])

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
        self.assertEqual(inputs.gps_file, os.path.abspath(self.test_gps_file))
        self.assertEqual(len(inputs.read_gps_file()), 3)

    def test_gps_file_set_fail(self):
        inputs = bilby_pipe.main.Input()
        gps_file = 'tests/nonexistant_file.txt'
        with self.assertRaises(FileNotFoundError):
            inputs.gps_file = gps_file

    def test_frequency_domain_source_model(self):
        inputs = bilby_pipe.main.Input()
        inputs.frequency_domain_source_model = 'lal_binary_black_hole'
        self.assertEqual(inputs.frequency_domain_source_model, 'lal_binary_black_hole')

    def test_frequency_domain_source_model_to_bilby(self):
        inputs = bilby_pipe.main.Input()
        inputs.frequency_domain_source_model = 'lal_binary_black_hole'
        self.assertEqual(inputs.bilby_frequency_domain_source_model,
                         bilby.gw.source.lal_binary_black_hole)

    def test_frequency_domain_source_model_to_bilby_fail(self):
        inputs = bilby_pipe.main.Input()
        inputs.frequency_domain_source_model = 'not_a_source_model'
        with self.assertRaises(BilbyPipeError):
            inputs.bilby_frequency_domain_source_model


if __name__ == '__main__':
    unittest.main()
