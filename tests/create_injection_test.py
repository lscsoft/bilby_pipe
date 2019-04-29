import os
import shutil
import unittest
import json

import bilby
import pandas as pd

import bilby_pipe
from bilby_pipe.utils import BilbyPipeError


class TestParser(unittest.TestCase):
    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.outdir = "outdir"
        self.example_prior_file = "tests/example_prior.prior"
        self.known_args_list = [
            "tests/test_main_input.ini",
            "--outdir",
            self.outdir,
            "--label",
            "TEST",
            "--prior-file",
            self.example_prior_file,
            "--n-injection",
            "3",
        ]
        self.parser = bilby_pipe.create_injections.create_parser()
        self.args = self.parser.parse_args(self.known_args_list)

    def tearDown(self):
        try:
            shutil.rmtree(self.outdir)
        except FileNotFoundError:
            pass
        del self.args

    def test_parser(self):
        self.assertEqual(self.args.label, "TEST")
        self.assertEqual(self.args.outdir, self.outdir)
        self.assertEqual(self.args.prior_file, self.example_prior_file)
        self.assertEqual(self.args.n_injection, 3)

    def test_init(self):
        inputs = bilby_pipe.create_injections.CreateInjectionInput(self.args, [])
        self.assertEqual(inputs.label, "TEST")
        self.assertEqual(inputs.outdir, os.path.relpath(self.outdir))
        self.assertEqual(inputs.prior_file, self.example_prior_file)
        self.assertEqual(inputs.n_injection, 3)

    def test_n_injections_not_set(self):
        self.args.n_injection = None
        inputs = bilby_pipe.create_injections.CreateInjectionInput(self.args, [])
        with self.assertRaises(BilbyPipeError):
            inputs.n_injection

    def test_unknown_prior_file(self):
        self.args.prior_file = "not_a_file"
        with self.assertRaises(FileNotFoundError):
            bilby_pipe.create_injections.CreateInjectionInput(self.args, [])

    def test_unknown_prior(self):
        inputs = bilby_pipe.create_injections.CreateInjectionInput(self.args, [])
        with self.assertRaises(AttributeError):
            inputs.priors = "lksjdf"

    def test_prior(self):
        inputs = bilby_pipe.create_injections.CreateInjectionInput(self.args, [])
        priors = bilby.core.prior.PriorDict(self.example_prior_file)
        self.assertEqual(priors, inputs.priors)

    def test_create_injection_file(self):
        inputs = bilby_pipe.create_injections.CreateInjectionInput(self.args, [])
        filename = os.path.join(self.outdir, "test_injection_file.h5")
        self.assertFalse(os.path.exists(filename))
        inputs.create_injection_file(filename)
        self.assertTrue(os.path.exists(filename))

        with open(filename, "r") as file:
            data = json.load(file, object_hook=bilby.core.result.decode_bilby_json)
        self.assertTrue(data.keys(), ["injections", "prior"])

        # prior = bilby.core.prior.PriorDict(self.example_prior_file)
        # self.assertEqual(sorted(data['prior'].keys()),
        #                  sorted(prior.keys()))

        df = data["injections"]
        self.assertEqual(type(df), pd.core.frame.DataFrame)
        self.assertEqual(len(df), inputs.n_injection)


if __name__ == "__main__":
    unittest.main()
