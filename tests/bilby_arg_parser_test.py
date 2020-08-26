import os
import shutil
import sys
import unittest
from unittest.mock import patch

from bilby_pipe.bilbyargparser import BilbyArgParser
from bilby_pipe.data_analysis import create_analysis_parser
from bilby_pipe.main import parse_args
from bilby_pipe.parser import create_parser
from bilby_pipe.utils import convert_string_to_dict


class TestBilbyArgParser(unittest.TestCase):
    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.outdir = "outdir"

    def tearDown(self):
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)

    def test_normalising_args(self):
        args_list = ["--sample_kwargs={'a':1}", "--_n=param"]
        bbargparser = BilbyArgParser()
        args, unknown_args = bbargparser.parse_known_args(args_list)
        self.assertTrue("param" in unknown_args)
        self.assertTrue("--sample-kwargs" in unknown_args)

    def test_args_string(self):
        bbargparser = BilbyArgParser()
        arg_key = "--key"
        arg_val = "val"
        args_string = f"{arg_key} {arg_val}"
        args, unknown_args = bbargparser.parse_known_args(args=args_string)
        self.assertTrue(arg_val in unknown_args)

    def test_arg_input_from_sys(self):
        bbargparser = BilbyArgParser()
        arg_key = "--key"
        arg_val = "val"
        args_list = [arg_key, arg_val]
        with patch.object(sys, "argv", args_list):
            args, unknown_args = bbargparser.parse_known_args()
            self.assertTrue(arg_val in unknown_args)

    def test_detectors_single(self):
        args_list = [
            "tests/test_dag_ini_file.ini",
            "--detectors",
            "H1",
            "--detectors",
            "L1",
        ]
        parser = create_analysis_parser()
        args, unknown_args = parse_args(args_list, parser)
        self.assertNotEqual(args.detectors, ["'H1'", "'L1'"], args.detectors)
        self.assertEqual(args.detectors, ["H1", "L1"], args.detectors)

    def test_detectors_double(self):
        args_list = ["tests/test_bilbyargparser.ini"]
        parser = create_analysis_parser()
        args, unknown_args = parse_args(args_list, parser)
        self.assertNotEqual(args.detectors, ["'H1'", "'L1'"], args.detectors)
        self.assertEqual(args.detectors, ["H1", "L1"], args.detectors)


class TestBilbyConfigFileParser(unittest.TestCase):
    def setUp(self):
        self.test_ini_filename = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "TEST_CONFIG.ini"
        )
        self.parser = create_parser(top_level=True)

    def tearDown(self):
        if os.path.exists(self.test_ini_filename):
            os.remove(self.test_ini_filename)

    def write_tempory_ini_file(self, lines):
        lines.append("accounting: test")
        with open(self.test_ini_filename, "a") as file:
            for line in lines:
                print(line, file=file)

        print(f"File{self.test_ini_filename}, content:")
        print("-------BEGIN-------")
        with open(self.test_ini_filename, "r") as file:
            for line in file:
                print(line.replace("\n", ""))
        print("-------END---------")

    def test_simple(self):
        self.write_tempory_ini_file([])
        args, unknown_args = parse_args([self.test_ini_filename], self.parser)
        self.assertEqual(args.accounting, "test")

    def test_sampler_kwargs_flat(self):
        kwargs_expected = dict(walks=1000)
        lines = ["sampler-kwargs: {walks:1000}"]
        self.write_tempory_ini_file(lines)
        args, unknown_args = parse_args([self.test_ini_filename], self.parser)
        self.assertEqual(convert_string_to_dict(args.sampler_kwargs), kwargs_expected)

    def test_sampler_kwargs_flat_multiline(self):
        kwargs_expected = dict(walks=1000, nact=5)
        lines = ["sampler-kwargs: {walks:1000,", "nact=5}"]
        self.write_tempory_ini_file(lines)
        args, unknown_args = parse_args([self.test_ini_filename], self.parser)
        self.assertEqual(convert_string_to_dict(args.sampler_kwargs), kwargs_expected)

    def test_sampler_kwargs_flat_multiline_no_comma(self):
        kwargs_expected = dict(walks=1000, nact=5)
        lines = ["sampler-kwargs: {walks:1000", "nact=5}"]
        self.write_tempory_ini_file(lines)
        args, unknown_args = parse_args([self.test_ini_filename], self.parser)
        self.assertEqual(convert_string_to_dict(args.sampler_kwargs), kwargs_expected)

    def test_sampler_kwargs_flat_multiline_with_space(self):
        kwargs_expected = dict(walks=1000, nact=5)
        lines = ["sampler-kwargs: {walks:1000", "   nact=5}"]
        self.write_tempory_ini_file(lines)
        args, unknown_args = parse_args([self.test_ini_filename], self.parser)
        self.assertEqual(convert_string_to_dict(args.sampler_kwargs), kwargs_expected)

    def test_sampler_kwargs_flat_multiline_end_comma(self):
        kwargs_expected = dict(walks=1000, nact=5)
        lines = ["sampler-kwargs: {walks:1000", "   nact=5,}"]
        self.write_tempory_ini_file(lines)
        args, unknown_args = parse_args([self.test_ini_filename], self.parser)
        self.assertEqual(convert_string_to_dict(args.sampler_kwargs), kwargs_expected)

    def test_sampler_kwargs_flat_long_multiline(self):
        kwargs_expected = dict(walks=1000, nact=5, test=1, blah="a")
        lines = ["sampler-kwargs: {walks:1000", "nact=5, test:1", "    blah=a}"]
        self.write_tempory_ini_file(lines)
        args, unknown_args = parse_args([self.test_ini_filename], self.parser)
        self.assertEqual(convert_string_to_dict(args.sampler_kwargs), kwargs_expected)

    def test_sampler_kwargs_empty(self):
        kwargs_expected = dict()
        kwargs_str = "{}"
        lines = [f"sampler-kwargs: {kwargs_str}"]
        self.write_tempory_ini_file(lines)
        args, unknown_args = parse_args([self.test_ini_filename], self.parser)
        self.assertEqual(convert_string_to_dict(args.sampler_kwargs), kwargs_expected)

    def test_prior_dict(self):
        kwargs_str = '{a=Uniform(name="a", minimum=0, maximum=1)}'
        lines = [f"prior-dict: {kwargs_str}"]
        self.write_tempory_ini_file(lines)
        args, unknown_args = parse_args([self.test_ini_filename], self.parser)
        self.assertEqual(args.prior_dict, kwargs_str)

    def test_prior_dict_multiline(self):
        kwargs_str = "{a: Uniform(name='a', minimum=0, maximum=1), b: 1}"
        lines = ["prior-dict: {a: Uniform(name='a', minimum=0, maximum=1)", "b: 1}"]
        self.write_tempory_ini_file(lines)
        args, unknown_args = parse_args([self.test_ini_filename], self.parser)
        self.assertEqual(args.prior_dict, kwargs_str)


if __name__ == "__main__":
    unittest.main()
