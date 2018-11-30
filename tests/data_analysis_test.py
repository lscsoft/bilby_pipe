import unittest
import shutil

from bilby_pipe.main import parse_args
from bilby_pipe.data_analysis import (
    DataAnalysisInput, create_parser)


class TestDataAnalysisInput(unittest.TestCase):

    def setUp(self):
        self.outdir = 'test_outdir'
        self.default_args_list = ['--ini', 'tests/test_data_analysis.ini',
                                  '--outdir', self.outdir]
        self.parser = create_parser()
        self.inputs = DataAnalysisInput(
            *parse_args(self.default_args_list, self.parser))

    def tearDown(self):
        del self.default_args_list
        del self.parser
        del self.inputs
        shutil.rmtree(self.outdir)

    def test_run_label(self):
        self.assertEqual(
            self.inputs.run_label, '{}_{}_{}_{}'.format(
                self.inputs.label, ''.join(self.inputs.detectors),
                self.inputs.sampler, self.inputs.process))

    def test_unset_sampling_seed(self):
        self.assertEqual(type(self.inputs.sampling_seed), int)

    def test_set_sampling_seed(self):
        args_list = self.default_args_list + ['--sampling-seed', '1']
        inputs = DataAnalysisInput(
            *parse_args(args_list, self.parser))
        self.assertEqual(inputs.sampling_seed, 1)

    def test_set_reference_frequency(self):
        args_list = self.default_args_list + ['--reference-frequency', '10']
        inputs = DataAnalysisInput(
            *parse_args(args_list, self.parser))
        self.assertEqual(inputs.reference_frequency, 10)

    def test_set_sampling_kwargs_ini(self):
        self.assertEqual(self.inputs.sampler_kwargs, dict(a=1, b=2))


if __name__ == '__main__':
    unittest.main()
