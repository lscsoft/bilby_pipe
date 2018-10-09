import os
import unittest
from argparse import Namespace

import bilby_pipe


class TestInput(unittest.TestCase):

    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.test_args = Namespace(
            ini='file.ini', submit=True, outdir='outdir', label='label',
            accounting='accounting.group', include_detectors='H1 L1',
            coherence_test=False, executable_library=self.directory,
            executable='executable.py', exe_help=False,
            X509=os.path.join(self.directory, 'X509.txt'))
        self.test_unknown_args = ['--argument', 'value']
        self.inputs = bilby_pipe.Input(self.test_args, self.test_unknown_args)

    def tearDown(self):
        del self.test_args
        del self.inputs

    def test_outdir(self):
        self.assertEqual(self.inputs.outdir, self.test_args.outdir)


if __name__ == '__main__':
    unittest.main()
