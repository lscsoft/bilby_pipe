import unittest
import shutil
import os
from argparse import Namespace

import subprocess
import deepdish

from bilby_pipe.main import parse_args
from bilby_pipe import create_injections
from bilby_pipe.data_generation import (
    DataGenerationInput, create_generation_parser)


class TestDataGenerationInput(unittest.TestCase):

    def setUp(self):
        self.outdir = 'test_outdir'
        self.default_args_list = ['--ini', 'tests/test_data_generation.ini',
                                  '--outdir', self.outdir]
        self.parser = create_generation_parser()
        self.inputs = DataGenerationInput(
            *parse_args(self.default_args_list, self.parser))
        self.gps_file = 'tests/gps_file.txt'

    def tearDown(self):
        del self.default_args_list
        del self.parser
        del self.inputs
        shutil.rmtree(self.outdir)

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

    # def test_set_gracedb(self):
    #     # Attempt to download data: will fail at the CalledProcessError due
    #     # to not being on a cluster
    #     with self.assertRaises(subprocess.CalledProcessError):
    #         self.inputs.gracedb = 'G184098'
    #     # Check it at least downloaded the JSON file correctly
    #     self.assertTrue(os.path.isfile(os.path.join(self.outdir, 'data', 'G184098.json')))

    def test_gps_file(self):
        args_list = ['--ini', 'tests/test_data_generation.ini',
                     '--outdir', self.outdir, '--gps-file', self.gps_file]
        with self.assertRaises(subprocess.CalledProcessError):
            self.inputs = DataGenerationInput(
                *parse_args(args_list, self.parser))

    def test_injections_no_file(self):
        args_list = ['--ini', 'tests/test_data_generation.ini',
                     '--outdir', self.outdir,
                     '--injection-file', 'not_a_file']
        with self.assertRaises(FileNotFoundError):
            self.inputs = DataGenerationInput(
                *parse_args(args_list, self.parser))

    def test_injections(self):
        inj_args = Namespace(
            prior_file='tests/example_prior.prior', n_injection=3,
            outdir=self.outdir, label='label')
        inj_inputs = create_injections.CreateInjectionInput(
            inj_args, [])
        injection_file_name = os.path.join(self.outdir, 'injection_file.h5')
        inj_inputs.create_injection_file(injection_file_name)

        args_list = ['--ini', 'tests/test_data_generation.ini',
                     '--outdir', self.outdir,
                     '--injection-file', injection_file_name]
        self.inputs = DataGenerationInput(
            *parse_args(args_list, self.parser))

        # Check the injections match by idx
        injection_file_dict = deepdish.io.load(injection_file_name)
        self.assertEqual(self.inputs.meta_data['injection_parameters'],
                         injection_file_dict['injections'].iloc[self.inputs.idx].to_dict())

        self.inputs.save_interferometer_list()
        self.assertTrue(os.path.isfile(os.path.join(
            self.outdir, 'data', '{}_{}_data_dump.h5'.format(
                self.inputs.label, self.inputs.idx))))

        self.assertEqual(self.inputs.injection_file, os.path.abspath(injection_file_name))


if __name__ == '__main__':
    unittest.main()
