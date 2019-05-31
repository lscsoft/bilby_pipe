import sys
import os
import unittest
import shutil

from unittest.mock import patch

from bilby_pipe.main import parse_args
from bilby_pipe.data_analysis import create_analysis_parser
from bilby_pipe.bilbyargparser import BilbyArgParser


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
        args_string = "{} {}".format(arg_key, arg_val)
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
