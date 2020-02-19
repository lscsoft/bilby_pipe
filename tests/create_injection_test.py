import os
import shutil
import unittest

import numpy as np

import bilby_pipe
from bilby_pipe.input import Input
from bilby_pipe.utils import BilbyPipeError, parse_args


class TestParser(unittest.TestCase):
    def test_parser_defaults(self):
        example_prior_file = "tests/example_prior.prior"

        known_args_list = [example_prior_file, "-n", "1"]
        parser = bilby_pipe.create_injections.create_parser()
        args, unknown_args = parse_args(known_args_list, parser)

        self.assertEqual(args.prior_file, example_prior_file)
        self.assertEqual(args.n_injection, 1)
        self.assertEqual(args.extension, "dat")

    def test_parser_with_prior_file(self):
        example_prior_file = "tests/example_prior.prior"

        known_args_list = [example_prior_file, "--n-injection", "3", "-s", "1234"]
        parser = bilby_pipe.create_injections.create_parser()
        args, unknown_args = parse_args(known_args_list, parser)

        self.assertEqual(args.prior_file, example_prior_file)
        self.assertEqual(args.n_injection, 3)
        self.assertEqual(args.generation_seed, 1234)

    def test_parser_with_default_prior_file(self):
        known_args_list = ["4s", "--n-injection", "3"]
        parser = bilby_pipe.create_injections.create_parser()
        args, unknown_args = parse_args(known_args_list, parser)

        self.assertEqual(args.prior_file, "4s")
        self.assertEqual(args.n_injection, 3)

    def test_parser_with_json(self):
        example_prior_file = "tests/example_prior.prior"

        known_args_list = [example_prior_file, "--n-injection", "3", "-e", "json"]
        parser = bilby_pipe.create_injections.create_parser()
        args, unknown_args = parse_args(known_args_list, parser)

        self.assertEqual(args.extension, "json")


class TestCreateInjections(unittest.TestCase):
    def setUp(self):
        self.outdir = "outdir"
        self.example_prior_file = "tests/example_prior.prior"
        self.filename = "{}/injection.dat".format(self.outdir)

    def tearDown(self):
        try:
            shutil.rmtree(self.outdir)
        except FileNotFoundError:
            pass

    def test_create_injection_file(self):
        filename = "{}/injections.dat".format(self.outdir)
        prior_file = self.example_prior_file
        n_injection = 3
        bilby_pipe.create_injections.create_injection_file(
            filename,
            n_injection,
            prior_file=prior_file,
            generation_seed=None,
            extension="dat",
        )
        self.assertTrue(os.path.isfile(filename))
        injections = np.genfromtxt(filename, names=True)
        self.assertEqual(len(injections), n_injection)

    def test_create_injection_file_dat_ext(self):
        filename = "{}/injections".format(self.outdir)
        prior_file = self.example_prior_file
        n_injection = 3
        bilby_pipe.create_injections.create_injection_file(
            filename,
            n_injection,
            prior_file=prior_file,
            generation_seed=None,
            extension="dat",
        )
        actual_filename = filename + ".dat"
        self.assertTrue(os.path.isfile(actual_filename))
        df = Input.read_dat_injection_file(actual_filename)
        self.assertEqual(len(df), n_injection)

    def test_create_injection_file_json_ext(self):
        filename = "{}/injections".format(self.outdir)
        prior_file = self.example_prior_file
        n_injection = 3
        bilby_pipe.create_injections.create_injection_file(
            filename,
            n_injection,
            prior_file=prior_file,
            generation_seed=None,
            extension="json",
        )
        actual_filename = filename + ".json"
        self.assertTrue(os.path.isfile(actual_filename))
        df = Input.read_json_injection_file(actual_filename)
        self.assertEqual(len(df), n_injection)

    def test_create_injection_file_json(self):
        filename = "{}/injections.json".format(self.outdir)
        prior_file = self.example_prior_file
        n_injection = 3
        bilby_pipe.create_injections.create_injection_file(
            filename,
            n_injection,
            prior_file=prior_file,
            generation_seed=None,
            extension="dat",
        )
        actual_filename = filename
        self.assertTrue(os.path.isfile(actual_filename))
        df = Input.read_json_injection_file(actual_filename)
        self.assertEqual(len(df), n_injection)

    def test_create_injection_file_generation_seed(self):
        filename = "{}/injections".format(self.outdir)
        prior_file = self.example_prior_file
        n_injection = 3
        bilby_pipe.create_injections.create_injection_file(
            filename + "_A", n_injection, prior_file=prior_file, generation_seed=123
        )
        injectionsA = np.genfromtxt(filename + "_A.dat", names=True)

        bilby_pipe.create_injections.create_injection_file(
            filename + "_B", n_injection, prior_file=prior_file, generation_seed=123
        )
        injectionsB = np.genfromtxt(filename + "_B.dat", names=True)

        bilby_pipe.create_injections.create_injection_file(
            filename + "_C", n_injection, prior_file=prior_file, generation_seed=321
        )
        injectionsC = np.genfromtxt(filename + "_C.dat", names=True)

        self.assertTrue(np.all(injectionsA == injectionsB))
        self.assertFalse(np.all(injectionsA == injectionsC))

    def test_n_injection_error(self):
        with self.assertRaises(BilbyPipeError):
            n_injection = None
            bilby_pipe.create_injections.create_injection_file(
                self.filename, n_injection, prior_file=self.example_prior_file
            )

        with self.assertRaises(BilbyPipeError):
            n_injection = -1
            bilby_pipe.create_injections.create_injection_file(
                self.filename, n_injection, prior_file=self.example_prior_file
            )

        with self.assertRaises(BilbyPipeError):
            n_injection = np.inf
            bilby_pipe.create_injections.create_injection_file(
                self.filename, n_injection, prior_file=self.example_prior_file
            )

    def test_unknown_prior_file(self):
        prior_file = "not_a_file"
        with self.assertRaises(FileNotFoundError):
            bilby_pipe.create_injections.create_injection_file(
                self.filename, 1, prior_file=prior_file
            )

    def test_none_prior_file(self):
        prior_file = None
        with self.assertRaises(BilbyPipeError):
            bilby_pipe.create_injections.create_injection_file(
                self.filename, 1, prior_file=prior_file
            )

    def test_unknown_ext(self):
        with self.assertRaises(BilbyPipeError):
            bilby_pipe.create_injections.create_injection_file(
                "test", 1, self.example_prior_file, extension="other"
            )

    def test_unknown_ext_from_filename(self):
        with self.assertRaises(BilbyPipeError):
            bilby_pipe.create_injections.create_injection_file(
                "test.other", 1, self.example_prior_file
            )


if __name__ == "__main__":
    unittest.main()
