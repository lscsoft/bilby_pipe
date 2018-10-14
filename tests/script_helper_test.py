import unittest

import bilby_pipe
import bilby


class TestScriptHelper(unittest.TestCase):

    def setUp(self):
        self.default_args_list = ['--ini', 'tests/test_script_helper_ini_file.ini']
        self.parser = bilby_pipe.script_helper.create_default_parser()

    def tearDown(self):
        del self.default_args_list
        del self.parser

    def test_script_inputs_no_parser_provided(self):
        keys_to_check = ['calibration', 'duration', 'sampling_frequency',
                         'psd_duration', 'minimum_frequency']
        default_inupts = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=self.default_args_list)
        inputs = bilby_pipe.script_helper.ScriptInput(
            args_list=self.default_args_list)
        self.assertTrue(all([
            getattr(inputs, key) == getattr(default_inupts, key)
            for key in keys_to_check]))

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

    def test_script_inputs_detectors_from_command_line_individually(self):
        args_list = self.default_args_list + ['--detectors', 'H1', '--detectors', 'L1']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    def test_script_inputs_detectors_from_command_line_as_string(self):
        args_list = self.default_args_list + ['--detectors', 'H1 L1']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    def test_script_inputs_detectors_from_command_line_out_of_order(self):
        args_list = self.default_args_list + ['--detectors', 'L1 H1']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    def test_script_inputs_detectors_from_command_line_as_delimited_list(self):
        args_list = self.default_args_list + ['--detectors', '[L1, H1]']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)

    def test_script_inputs_detectors_from_command_line_as_undelimited_list(self):
        args_list = self.default_args_list + ['--detectors', '[L1 H1]']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    def test_script_inputs_detectors_from_command_line_as_string_list(self):
        args_list = self.default_args_list + ['--detectors', '["L1", "H1"]']
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args_list = self.default_args_list + ['--detectors', "['L1', 'H1']"]
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

    def test_script_inputs_detectors_setter_must_be_list(self):
        args_list = self.default_args_list
        input = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        with self.assertRaises(ValueError):
            input.detectors = 7

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

    # def test_unset_sampler_kwargs_is_none(self):
    #     args_list = self.default_args_list
    #     inputs = bilby_pipe.script_helper.ScriptInput(
    #         parser=self.parser)
    #     self.assertIsNone(inputs.sampler_kwargs)

    def test_set_sampler_kwargs_to_none(self):
        args_list = self.default_args_list
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        inputs.sampler_kwargs = None
        self.assertIsNone(inputs.sampler_kwargs)

    def test_set_sampler_kwargs_as_dict(self):
        args_list = self.default_args_list
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        inputs.sampler_kwargs = "{'nlive': 100}"
        self.assertDictEqual(inputs.sampler_kwargs, dict(nlive=100))

    def test_set_sampler_kwargs_raises_value_error(self):
        args_list = self.default_args_list
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        with self.assertRaises(ValueError):
            inputs.sampler_kwargs = "{nlive: 100}"

    def test_label(self):
        args_list = self.default_args_list
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        self.assertEqual(inputs.run_label, 'label_H1L1')

    def test_priors(self):
        args_list = self.default_args_list
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        trigger_time = 1
        inputs.trigger_time = trigger_time
        prior = bilby.gw.prior.BBHPriorSet()
        prior['geocent_time'] = bilby.core.prior.Uniform(
            trigger_time - 0.5, trigger_time + 0.5,
            name='geocent_time', latex_label='$t_c$', unit='$s$')
        self.assertEqual(inputs.priors.__repr__(), prior.__repr__())

    def test_waveform_generator(self):
        args_list = self.default_args_list
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        inputs.frequency_domain_source_model =\
            bilby.gw.source.lal_binary_black_hole
        waveform_generator = bilby.gw.waveform_generator.WaveformGenerator(
            duration=4, sampling_frequency=4096, start_time=0,
            frequency_domain_source_model=bilby.gw.source.lal_binary_black_hole,
            parameter_conversion=bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters,
            waveform_arguments=inputs.waveform_arguments
        )
        self.assertEqual(inputs.waveform_generator.__repr__(),
                         waveform_generator.__repr__())

    def test_waveform_arguments(self):
        args_list = self.default_args_list
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=args_list)
        waveform_arguments = dict(
            reference_frequency=10.0, waveform_approximant="'test'",
            minimum_frequency=100.0)
        self.assertDictEqual(inputs.waveform_arguments, waveform_arguments)

    def test_ifos_raise_exception_when_data_not_found(self):
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=self.default_args_list)
        inputs.frame_caches = None
        with self.assertRaises(Exception):
            inputs.ifos

    def test_ifos_when_provided(self):
        inputs = bilby_pipe.script_helper.ScriptInput(
            parser=self.parser, args_list=self.default_args_list)
        ifos = bilby.gw.detector.InterferometerList(['H1'])
        inputs._ifos = ifos
        self.assertEqual(inputs.ifos.__repr__(), ifos.__repr__())


if __name__ == '__main__':
    unittest.main()
