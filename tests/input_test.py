import os
import unittest
from argparse import Namespace
import copy
import shutil

import bilby_pipe


class TestInput(unittest.TestCase):

    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.outdir = 'outdir'
        self.test_args = Namespace(
            ini='file.ini', submit=True, outdir=self.outdir, label='label',
            accounting='accounting.group', include_detectors='H1',
            coherence_test=False, executable='bbh_from_gracedb.py', exe_help=False,
            X509=os.path.join(self.directory, 'X509.txt'), queue=1, create_summary=False,
            sampler=['nestle'])
        self.test_unknown_args = ['--argument', 'value']
        self.inputs = bilby_pipe.Input(self.test_args, self.test_unknown_args)

    def tearDown(self):
        shutil.rmtree(self.outdir)
        del self.test_args
        del self.inputs

    def test_ini(self):
        self.assertEqual(self.inputs.ini, self.test_args.ini)

    def test_submit(self):
        self.assertEqual(self.inputs.submit, self.test_args.submit)

    def test_outdir(self):
        self.assertEqual(os.path.abspath(self.test_args.outdir),
                         self.inputs.outdir)

    def test_label(self):
        self.assertEqual(self.inputs.label, self.test_args.label)

    def test_executable_from_path(self):
        executable = os.path.join(
            self.directory, self.inputs.executable)
        test_args = copy.copy(self.test_args)
        test_args.executable = executable
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
        self.assertEqual(inputs.executable, executable)

    def test_executable_fail(self):
        test_args = copy.copy(self.test_args)
        test_args.executable = 'random_string'
        with self.assertRaises(ValueError):
            bilby_pipe.Input(test_args, self.test_unknown_args)

    def test_coherence_test(self):
        self.assertEqual(self.inputs.coherence_test,
                         self.test_args.coherence_test)

    def test_accounting(self):
        self.assertEqual(self.inputs.accounting, self.test_args.accounting)

    def test_include_detectors_single(self):
        test_args = copy.copy(self.test_args)
        test_args.include_detectors = 'L1'
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
        self.assertEqual(inputs.include_detectors, ['L1'])

        test_args.include_detectors = ['L1']
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
        self.assertEqual(inputs.include_detectors, ['L1'])

        with self.assertRaises(ValueError):
            test_args.include_detectors = 'A1'
            inputs = bilby_pipe.Input(test_args, self.test_unknown_args)

        with self.assertRaises(ValueError):
            test_args.include_detectors = None
            inputs = bilby_pipe.Input(test_args, self.test_unknown_args)

    def test_include_detectors_multiple(self):
        test_args = copy.copy(self.test_args)
        test_args.include_detectors = 'H1 L1'
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
        self.assertEqual(inputs.include_detectors, ['H1', 'L1'])

        test_args.include_detectors = 'L1 H1'
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
        self.assertEqual(inputs.include_detectors, ['H1', 'L1'])

        test_args.include_detectors = ['L1 H1']
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
        self.assertEqual(inputs.include_detectors, ['H1', 'L1'])

        test_args.include_detectors = ['L1', 'H1']
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
        self.assertEqual(inputs.include_detectors, ['H1', 'L1'])

        test_args.include_detectors = ['H1', 'L1']
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
        self.assertEqual(inputs.include_detectors, ['H1', 'L1'])

        test_args.include_detectors = ['H1', 'l1']
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)

        with self.assertRaises(ValueError):
            test_args.include_detectors = ['H1', 'error']
            inputs = bilby_pipe.Input(test_args, self.test_unknown_args)

    def test_x506_fail(self):
        with self.assertRaises(ValueError):
            test_args = copy.copy(self.test_args)
            test_args.X509 = 'random_string'
            bilby_pipe.Input(test_args, self.test_unknown_args)

    def test_x506_from_path(self):
        test_args = copy.copy(self.test_args)
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
        self.assertEqual(inputs.x509userproxy, test_args.X509)

    def test_x509_environ_unset(self):
        test_args = copy.copy(self.test_args)
        test_args.X509 = None
        os.environ.unsetenv('X509_USER_PROXY')
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
        self.assertEqual(inputs.x509userproxy, None)

    def test_x509_from_env_variable(self):
        test_args = copy.copy(self.test_args)
        os.environ['X509_USER_PROXY'] = os.path.realpath(test_args.X509)
        test_args.X509 = None
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
        X509_cached_copy = os.path.abspath(os.path.join(test_args.outdir,
                                                        '.X509.txt'))
        self.assertEqual(inputs.x509userproxy, X509_cached_copy)


if __name__ == '__main__':
    unittest.main()
