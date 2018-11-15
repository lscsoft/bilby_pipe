import os
import unittest
from argparse import Namespace
import copy

import bilby_pipe


class TestDag(unittest.TestCase):

    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.test_args = Namespace(
            ini='tests/test_dag_ini_file.ini', submit=False, outdir='outdir', label='label',
            accounting='accounting.group', detectors='H1',
            coherence_test=False, X509=os.path.join(self.directory, 'X509.txt'),
            queue=1, create_summary=False, sampler=['nestle'])
        self.test_unknown_args = ['--argument', 'value']
        self.inputs = bilby_pipe.main.MainInput(self.test_args, self.test_unknown_args)

    def tearDown(self):
        del self.test_args
        del self.inputs

    def test_jobs_creation(self):
        test_args = copy.copy(self.test_args)
        test_args.detectors = 'H1 L1'
        test_args.coherence_test = True
        inputs = bilby_pipe.main.MainInput(test_args, self.test_unknown_args)
        dag = bilby_pipe.main.Dag(inputs)
        expected_jobs = [dict(detectors=['H1', 'L1'], sampler='nestle'),
                         dict(detectors=['H1'], sampler='nestle'),
                         dict(detectors=['L1'], sampler='nestle')]
        self.assertEqual(dag.analyse_data_jobs_inputs, expected_jobs)

    # def test_build_submit(self):
    #     test_args = copy.copy(self.test_args)
    #     test_args.submit = True
    #     inputs = bilby_pipe.main.MainInput(test_args, self.test_unknown_args)
    #     dag = bilby_pipe.Dag(inputs)
    #     dag.build_submit()


if __name__ == '__main__':
    unittest.main()
