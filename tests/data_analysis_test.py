import unittest
import shutil

import bilby

from bilby_pipe.main import parse_args
from bilby_pipe.utils import BilbyPipeError
from bilby_pipe.data_analysis import DataAnalysisInput, create_analysis_parser


class TestDataAnalysisInput(unittest.TestCase):
    def setUp(self):
        self.outdir = "test_outdir"
        self.default_args_list = [
            "--ini",
            "tests/test_data_analysis.ini",
            "--outdir",
            self.outdir,
        ]
        self.parser = create_analysis_parser()
        self.inputs = DataAnalysisInput(
            *parse_args(self.default_args_list, self.parser), test=True
        )

    def tearDown(self):
        del self.default_args_list
        del self.parser
        del self.inputs
        shutil.rmtree(self.outdir)

    def test_cluster_setting(self):
        args_list = self.default_args_list
        args_list.append("--cluster")
        args_list.append("10")
        self.inputs = DataAnalysisInput(*parse_args(args_list, self.parser), test=True)
        self.assertEqual(self.inputs.cluster, 10)

    def test_process_setting(self):
        args_list = self.default_args_list
        args_list.append("--process")
        args_list.append("10")
        self.inputs = DataAnalysisInput(*parse_args(args_list, self.parser), test=True)
        self.assertEqual(self.inputs.process, 10)

    def test_unset_sampling_seed(self):
        self.assertEqual(type(self.inputs.sampling_seed), int)

    def test_set_sampling_seed(self):
        args_list = self.default_args_list + ["--sampling-seed", "1"]
        inputs = DataAnalysisInput(*parse_args(args_list, self.parser), test=True)
        self.assertEqual(inputs.sampling_seed, 1)

    def test_set_reference_frequency(self):
        args_list = self.default_args_list + ["--reference-frequency", "10"]
        inputs = DataAnalysisInput(*parse_args(args_list, self.parser), test=True)
        self.assertEqual(inputs.reference_frequency, 10)

    def test_set_sampler_ini(self):
        self.inputs = DataAnalysisInput(
            *parse_args(self.default_args_list, self.parser), test=True
        )
        self.assertEqual(self.inputs.sampler, "nestle")

    def test_set_sampler_command_line(self):
        args_list = self.default_args_list
        args_list.append("--sampler")
        args_list.append("emcee")
        self.inputs = DataAnalysisInput(*parse_args(args_list, self.parser), test=True)
        self.assertEqual(self.inputs.sampler, "emcee")

    def test_set_sampler_command_line_multiple_fail(self):
        args_list = self.default_args_list
        self.inputs = DataAnalysisInput(*parse_args(args_list, self.parser), test=True)
        with self.assertRaises(BilbyPipeError):
            self.inputs.sampler = ["dynesty", "nestle"]

    def test_direct_set_sampler(self):
        self.inputs.sampler = "dynesty"
        self.assertEqual(self.inputs.sampler, "dynesty")

    def test_set_sampling_kwargs_ini(self):
        self.assertEqual(self.inputs.sampler_kwargs, dict(a=1, b=2))

    def test_set_sampling_kwargs_direct(self):
        self.inputs.sampler_kwargs = "{'a':5, 'b':5}"
        self.assertEqual(self.inputs.sampler_kwargs, dict(a=5, b=5))

    def test_unset_sampling_kwargs(self):
        args, unknown_args = parse_args(self.default_args_list, self.parser)
        args.sampler_kwargs = None
        inputs = DataAnalysisInput(args, unknown_args, test=True)
        self.assertEqual(inputs.sampler_kwargs, None)

    def test_set_sampler_kwargs_fail(self):
        with self.assertRaises(BilbyPipeError):
            self.inputs.sampler_kwargs = "random_string"

    def test_set_frequency_domain_source_model(self):
        self.inputs.frequency_domain_source_model = "lal_binary_black_hole"
        self.assertEqual(
            self.inputs.frequency_domain_source_model, "lal_binary_black_hole"
        )

    def test_bilby_frequency_domain_source_model(self):
        self.inputs.frequency_domain_source_model = "lal_binary_black_hole"
        self.assertEqual(
            self.inputs.bilby_frequency_domain_source_model,
            bilby.gw.source.lal_binary_black_hole,
        )

    def test_unset_bilby_frequency_domain_source_model(self):
        self.inputs.frequency_domain_source_model = "not_a_source_model"
        with self.assertRaises(BilbyPipeError):
            print(self.inputs.bilby_frequency_domain_source_model)


if __name__ == "__main__":
    unittest.main()
