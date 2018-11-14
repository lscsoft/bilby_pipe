import unittest

import bilby_pipe


class TestGenerateInterferometerListInput(unittest.TestCase):

    def setUp(self):
        self.default_args_list = ['--ini', 'tests/test_generate_interferometer_list.ini']
        self.parser = bilby_pipe.generate_interferometer_list.create_parser()

    def tearDown(self):
        del self.default_args_list
        del self.parser

    def test_script_inputs_from_test_ini(self):
        inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
            parser=self.parser, args_list=self.default_args_list)
        self.assertEqual(inputs.calibration, 2)
        self.assertEqual(inputs.label, 'label')
        self.assertEqual(inputs.channel_names, ['name1', 'name2'])

    def test_interferometer_unset(self):
        inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
            parser=self.parser, args_list=self.default_args_list)
        with self.assertRaises(ValueError):
            inputs.interferometers

    def test_interferometer_set(self):
        inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
            parser=self.parser, args_list=self.default_args_list)
        inputs.interferometers = ['a', 'b']
        self.assertEqual(['a', 'b'], inputs.interferometers)

    def test_script_inputs_detectors_from_ini(self):
        inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
            parser=self.parser, args_list=self.default_args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    # def test_run_label(self):
    #     inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
    #         parser=self.parser, args_list=self.default_args_list)
    #     self.assertEqual(
    #         inputs.run_label, '{}_{}_{}'.format(
    #             inputs.label, ''.join(inputs.detectors), inputs.sampler))

    def test_script_inputs_detectors_from_command_line(self):
        args_list = self.default_args_list + ['--detectors', 'H1', '--detectors', 'L1']
        inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', 'H1 L1']
        inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', 'L1 H1']
        inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', '[L1, H1]']
        inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
            parser=self.parser, args_list=args_list)

        args_list = self.default_args_list + ['--detectors', '[L1 H1]']
        inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', '["L1", "H1"]']
        inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', "['L1', 'H1']"]
        inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    # def test_unset_sampling_seed(self):
    #     args_list = self.default_args_list
    #     inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
    #         parser=self.parser, args_list=args_list)
    #     self.assertEqual(type(inputs.sampling_seed), int)

    # def test_set_sampling_seed(self):
    #     args_list = self.default_args_list + ['--sampling-seed', '1']
    #     inputs = bilby_pipe.generate_interferometer_list.GenerateInterferometerListInput(
    #         parser=self.parser, args_list=args_list)
    #     self.assertEqual(inputs.sampling_seed, 1)


if __name__ == '__main__':
    unittest.main()
