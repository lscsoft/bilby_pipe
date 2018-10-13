import os
import unittest
from argparse import Namespace
import copy

import bilby_pipe


class TestScriptHelper(unittest.TestCase):

    def setUp(self):
        self.default_args_list = ['--ini', 'tests/test_script_helper_ini_file.ini']
        self.parser = bilby_pipe.script_helper.create_default_parser()

    def tearDown(self):
        del self.default_args_list
        del self.parser

    def test_script_inputs_from_test_ini(self):
        args = self.parser.parse_args(self.default_args_list)
        inputs = bilby_pipe.script_helper.ScriptInput(args)
        self.assertEqual(inputs.calibration, 2)
        self.assertEqual(inputs.label, 'label')
        self.assertEqual(inputs.channel_names, ['name1', 'name2'])
        self.assertEqual(inputs.phase_marginalization, True)
        self.assertEqual(inputs.sampler_kwargs, {'a': 1, 'b': 2})

    def test_script_inputs_detectors_from_ini(self):
        parsed_args = self.parser.parse_args(self.default_args_list)
        inputs = bilby_pipe.script_helper.ScriptInput(parsed_args)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    def test_script_inputs_detectors_from_command_line(self):
        args_list = self.default_args_list + ['--detectors', 'H1', '--detectors', 'L1']
        parsed_args = self.parser.parse_args(args_list)
        inputs = bilby_pipe.script_helper.ScriptInput(parsed_args)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', 'H1 L1']
        parsed_args = self.parser.parse_args(args_list)
        inputs = bilby_pipe.script_helper.ScriptInput(parsed_args)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', 'L1 H1']
        parsed_args = self.parser.parse_args(args_list)
        inputs = bilby_pipe.script_helper.ScriptInput(parsed_args)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', '[L1, H1]']
        parsed_args = self.parser.parse_args(args_list)
        inputs = bilby_pipe.script_helper.ScriptInput(parsed_args)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', '[L1 H1]']
        parsed_args = self.parser.parse_args(args_list)
        inputs = bilby_pipe.script_helper.ScriptInput(parsed_args)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', '["L1", "H1"]']
        parsed_args = self.parser.parse_args(args_list)
        inputs = bilby_pipe.script_helper.ScriptInput(parsed_args)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', "['L1', 'H1']"]
        parsed_args = self.parser.parse_args(args_list)
        inputs = bilby_pipe.script_helper.ScriptInput(parsed_args)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])


if __name__ == '__main__':
    unittest.main()
