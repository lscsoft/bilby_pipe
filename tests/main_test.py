import os
import unittest
import copy
import shutil

import bilby_pipe


class TestInput(unittest.TestCase):
    def setUp(self):
        pass

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
        with self.assertRaises(ValueError):
            inputs.detectors = 'G1'

        with self.assertRaises(ValueError):
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
        gps_file = 'tests/gps_file.txt'
        inputs.gps_file = gps_file
        self.assertEqual(inputs.gps_file, os.path.abspath(gps_file))
        self.assertEqual(len(inputs.read_gps_file()), 3)

    def test_gps_file_set_fail(self):
        inputs = bilby_pipe.main.Input()
        gps_file = 'tests/nonexistant_file.txt'
        with self.assertRaises(FileNotFoundError):
            inputs.gps_file = gps_file


class TestMainInput(unittest.TestCase):

    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.outdir = 'outdir'
        self.known_args_list = [
            'tests/test_main_input.ini', '--submit', '--outdir', self.outdir,
            '--X509', os.path.join(self.directory, 'X509.txt'),
            '--no-singularity']
        self.unknown_args_list = ['--argument', 'value']
        self.all_args_list = self.known_args_list + self.unknown_args_list
        self.parser = bilby_pipe.main.create_parser()
        self.args = self.parser.parse_args(self.known_args_list)
        self.inputs = bilby_pipe.main.MainInput(
            *self.parser.parse_known_args(self.all_args_list))

    def tearDown(self):
        shutil.rmtree(self.outdir)
        del self.args
        del self.inputs

    def test_ini(self):
        self.assertEqual(self.inputs.ini, os.path.abspath(self.args.ini))

    def test_ini_not_a_file(self):
        with self.assertRaises(ValueError):
            self.inputs.ini = 'not_a_file'

    def test_singularity_image_setting_fail(self):
        with self.assertRaises(ValueError):
            self.inputs.singularity_image = 10

        with self.assertRaises(FileNotFoundError):
            self.inputs.singularity_image = 'not_a_file'

    def test_use_singularity(self):
        self.inputs.use_singularity = True
        self.assertEqual(self.inputs.use_singularity, True)

        with self.assertRaises(ValueError):
            self.inputs.use_singularity = 10

    def test_setting_level_A_jobs(self):
        self.inputs.n_level_A_jobs = 10
        self.assertEqual(self.inputs.n_level_A_jobs, 10)

    def test_default_level_A_labels(self):
        self.inputs.n_level_A_jobs = 2
        self.assertEqual(self.inputs.level_A_labels, ['', ''])

    def test_setting_level_A_labels(self):
        self.inputs.level_A_labels = ['a', 'b']
        self.assertEqual(self.inputs.level_A_labels, ['a', 'b'])

    def test_submit(self):
        self.assertEqual(self.inputs.submit, self.args.submit)

    def test_label(self):
        self.assertEqual(self.inputs.label, self.args.label)

    def test_coherence_test(self):
        self.assertEqual(self.inputs.coherence_test,
                         self.args.coherence_test)

    def test_accounting(self):
        self.assertEqual(self.inputs.accounting, self.args.accounting)

    def test_detectors_single(self):
        # Test the detector set in the ini file
        self.assertEqual(self.inputs.detectors, ['H1'])

        # Test setting a single detector directly in the args as a string
        args = copy.copy(self.args)
        args.detectors = 'L1'
        inputs = bilby_pipe.main.MainInput(
            args, [])
        self.assertEqual(inputs.detectors, ['L1'])

        args.detectors = ['L1']
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.detectors, ['L1'])

        with self.assertRaises(ValueError):
            args.detectors = 'A1'
            inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)

        with self.assertRaises(ValueError):
            args.detectors = None
            inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)

    def test_detectors_multiple(self):
        args = copy.copy(self.args)
        args.detectors = 'H1 L1'
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args.detectors = 'L1 H1'
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args.detectors = ['L1 H1']
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args.detectors = ['L1', 'H1']
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args.detectors = ['H1', 'L1']
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.detectors, ['H1', 'L1'])

        args.detectors = ['H1', 'l1']
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)

        with self.assertRaises(ValueError):
            args.detectors = ['H1', 'error']
            inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)

    def test_x506_fail(self):
        with self.assertRaises(ValueError):
            args = copy.copy(self.args)
            args.X509 = 'random_string'
            bilby_pipe.main.MainInput(args, self.unknown_args_list)

    def test_x506_from_path(self):
        args = copy.copy(self.args)
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.x509userproxy, args.X509)

    def test_x509_environ_unset(self):
        args = copy.copy(self.args)
        args.X509 = None
        os.environ.unsetenv('X509_USER_PROXY')
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        self.assertEqual(inputs.x509userproxy, None)

    def test_x509_from_env_variable(self):
        args = copy.copy(self.args)
        os.environ['X509_USER_PROXY'] = os.path.realpath(args.X509)
        args.X509 = None
        inputs = bilby_pipe.main.MainInput(args, self.unknown_args_list)
        X509_cached_copy = os.path.abspath(os.path.join(args.outdir,
                                                        '.X509.txt'))
        self.assertEqual(inputs.x509userproxy, X509_cached_copy)


if __name__ == '__main__':
    unittest.main()
