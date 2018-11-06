import os
import unittest
from argparse import Namespace

import bilby_pipe


class TestDag(unittest.TestCase):

    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.test_args = Namespace(
            ini='file.ini', submit=False, outdir='outdir', label='label',
            accounting='accounting.group', include_detectors='H1',
            coherence_test=False, executable='bbh_from_gracedb.py',
            exe_help=False, X509=os.path.join(self.directory, 'X509.txt'),
            queue=1, create_summary=False, sampler=['nestle'])
        self.inputs = bilby_pipe.Input(self.test_args, [])

    def tearDown(self):
        del self.test_args
        del self.inputs

    def test_summary_creation(self):
        dag = bilby_pipe.Dag(self.inputs)
        bilby_pipe.webpages.create_summary_page(dag)
        self.assertTrue(
            os.path.isfile(os.path.join(self.inputs.outdir, 'summary.html')))


if __name__ == '__main__':
    unittest.main()
