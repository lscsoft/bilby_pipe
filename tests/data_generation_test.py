import unittest

from bilby_pipe.main import parse_args
from bilby_pipe.data_generation import (
    DataGenerationInput, create_parser)


class TestDataGenerationInput(unittest.TestCase):

    def setUp(self):
        self.default_args_list = ['--ini', 'tests/test_data_generation.ini']
        self.parser = create_parser()
        self.inputs = DataGenerationInput(
            *parse_args(self.default_args_list, self.parser))

    def tearDown(self):
        del self.default_args_list
        del self.parser
        del self.inputs

    def test_script_inputs_from_test_ini(self):
        self.assertEqual(self.inputs.calibration, 2)
        self.assertEqual(self.inputs.label, 'label')
        self.assertEqual(self.inputs.channel_names, ['name1', 'name2'])

    def test_interferometer_unset(self):
        with self.assertRaises(ValueError):
            self.inputs.interferometers

    def test_interferometer_set(self):
        self.inputs.interferometers = ['a', 'b']
        self.assertEqual(['a', 'b'], self.inputs.interferometers)

    def test_script_inputs_detectors_from_ini(self):
        self.assertEqual(self.inputs.detectors, ['H1', 'L1'])

    def test_script_inputs_detectors_from_command_line(self):
        args_list = self.default_args_list + ['--detectors', 'H1', '--detectors', 'L1']
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser))
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', 'H1 L1']
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser))
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', 'L1 H1']
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser))
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', '[L1, H1]']
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser))

        args_list = self.default_args_list + ['--detectors', '[L1 H1]']
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser))
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', '["L1", "H1"]']
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser))
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', "['L1', 'H1']"]
        inputs = DataGenerationInput(
            *parse_args(args_list, self.parser))
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    def test_detectors_not_understood(self):
        with self.assertRaises(ValueError):
            self.inputs.detectors = 10

    def test_minimum_frequency(self):
        self.inputs.minimum_frequency = 10
        self.assertEqual(self.inputs.minimum_frequency, 10)


if __name__ == '__main__':
    unittest.main()
