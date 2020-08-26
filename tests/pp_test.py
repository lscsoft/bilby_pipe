import os
import shutil
import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

import bilby
import bilby_pipe
import bilby_pipe.pp_test


class TestPP(unittest.TestCase):
    def setUp(self):
        self.outdir = "test_outdir"
        self.args = SimpleNamespace(
            directory=self.outdir,
            outdir=None,
            label=None,
            n=None,
            print=False,
            filter=None,
        )
        os.mkdir(self.outdir)

    def tearDown(self):
        shutil.rmtree(self.outdir)
        del self.outdir

    def create_fake_results(self):
        self.N_results = 3
        self.results_filenames = []
        self.priors = bilby.core.prior.PriorDict(
            dict(
                A=bilby.core.prior.Normal(0, 1, "A"),
                B=bilby.core.prior.Normal(0, 1, "B"),
            )
        )
        for i in range(self.N_results):
            result = bilby.core.result.Result()
            result.outdir = self.outdir
            result.label = f"label_{i}"
            result.search_parameter_keys = ["A", "B"]
            result.priors = self.priors
            result.posterior = pd.DataFrame(
                dict(A=np.random.normal(0, 1, 100), B=np.random.normal(0, 1, 100))
            )
            result.injection_parameters = dict(A=0, B=0)
            result.sampling_time = np.random.uniform(0, 1)
            result.meta_data = dict(
                likelihood=dict(
                    interferometers=dict(H1=dict(optimal_SNR=1), L1=dict(optimal_SNR=1))
                )
            )
            filename = f"{result.outdir}/{result.label}_result.json"
            result.save_to_file(filename)
            self.results_filenames.append(filename)

    def test_parser(self):
        directory = "directory"
        parser = bilby_pipe.pp_test.create_parser()
        args = parser.parse_args(
            [directory, "--outdir", self.outdir, "--label", "TEST", "-n", "10"]
        )
        self.assertEqual(args.directory, directory)
        self.assertEqual(args.outdir, self.outdir)
        self.assertEqual(args.label, "TEST")
        self.assertEqual(args.n, 10)

    def test_get_results_filename(self):
        self.create_fake_results()
        results_filenames = bilby_pipe.pp_test.get_results_filenames(self.args)
        self.assertEqual(sorted(results_filenames), sorted(self.results_filenames))

    def test_get_results_filename_with_n(self):
        n = 2
        self.create_fake_results()
        args = self.args
        args.n = n
        results_filenames = bilby_pipe.pp_test.get_results_filenames(args)
        self.assertEqual(len(results_filenames), n)

    def test_get_results_filename_no_file(self):
        with self.assertRaises(FileNotFoundError):
            bilby_pipe.pp_test.get_results_filenames(self.args)

    def test_read_in_result_list(self):
        self.create_fake_results()
        res = bilby_pipe.pp_test.read_in_result_list(self.args, self.results_filenames)
        self.assertEqual(len(res), self.N_results)
        self.assertIsInstance(res, bilby.core.result.ResultList)

    def test_main(self):
        self.create_fake_results()
        bilby_pipe.pp_test.main(self.args)


if __name__ == "__main__":
    unittest.main()
