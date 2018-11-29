import os
import unittest
import shutil
from argparse import Namespace

import bilby_pipe


class TestDag(unittest.TestCase):

    def setUp(self):
        self.outdir = 'test_outdir'
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.test_args = Namespace(
            ini='tests/test_main_input.ini', submit=False, outdir=self.outdir,
            label='label', accounting='accounting.group', detectors='H1',
            coherence_test=False, injection=False, injection_file=None,
            n_injection=None,
            X509=os.path.join(self.directory, 'X509.txt'),
            queue=1, create_summary=False, sampler=['nestle'])
        self.inputs = bilby_pipe.main.MainInput(self.test_args, [])

    def tearDown(self):
        del self.test_args
        del self.inputs
        shutil.rmtree(self.outdir)

    def test_summary_creation(self):
        dag = bilby_pipe.main.Dag(self.inputs)
        bilby_pipe.webpages.create_summary_page(dag)
        self.assertTrue(
            os.path.isfile(os.path.join(self.inputs.outdir, 'summary.html')))


if __name__ == '__main__':
    unittest.main()
