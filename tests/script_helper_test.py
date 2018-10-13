import unittest

import bilby_pipe


class TestScriptHelper(unittest.TestCase):

    def setUp(self):
        self.default_args_list = ['--ini', 'tests/test_script_helper_ini_file.ini']
        self.parser = bilby_pipe.script_helper.create_default_parser()

    def tearDown(self):
        del self.default_args_list
        del self.parser

    def test_script_inputs_from_test_ini(self):
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=self.default_args_list)
        self.assertEqual(inputs.calibration, 2)
        self.assertEqual(inputs.label, 'label')
        self.assertEqual(inputs.channel_names, ['name1', 'name2'])
        self.assertEqual(inputs.phase_marginalization, True)
        self.assertEqual(inputs.sampler_kwargs, {'a': 1, 'b': 2})

    def test_script_inputs_detectors_from_ini(self):
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=self.default_args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    def test_script_inputs_detectors_from_command_line(self):
        args_list = self.default_args_list + ['--detectors', 'H1', '--detectors', 'L1']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', 'H1 L1']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', 'L1 H1']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', '[L1, H1]']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)

        args_list = self.default_args_list + ['--detectors', '[L1 H1]']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', '["L1", "H1"]']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', "['L1', 'H1']"]
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    def test_unset_sampling_seed(self):
        args_list = self.default_args_list
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(type(inputs.sampling_seed), int)

    def test_set_sampling_seed(self):
        args_list = self.default_args_list + ['--sampling-seed', '1']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.sampling_seed, 1)


if __name__ == '__main__':
    unittest.main()
