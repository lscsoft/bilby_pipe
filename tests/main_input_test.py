import os
import unittest
import copy
import shutil

import bilby_pipe


class TestMainInput(unittest.TestCase):

    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.outdir = 'outdir'
        self.known_args_list = [
            'tests/test_main_input.ini', '--submit', '--outdir', self.outdir,
            '--X509', os.path.join(self.directory, 'X509.txt')]
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
        self.assertEqual(self.inputs.ini, self.args.ini)

    def test_submit(self):
        self.assertEqual(self.inputs.submit, self.args.submit)

    def test_outdir(self):
        self.assertEqual(os.path.abspath(self.args.outdir),
                         self.inputs.outdir)

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
