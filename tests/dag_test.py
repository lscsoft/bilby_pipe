import os
import unittest
from argparse import Namespace
import shutil

import bilby_pipe


class TestDag(unittest.TestCase):
    def setUp(self):
        self.outdir = "test_outdir"
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.test_args = Namespace(
            ini="tests/test_dag_ini_file.ini",
            submit=False,
            outdir=self.outdir,
            label="label",
            accounting="accounting.group",
            detectors="H1",
            coherence_test=False,
            injection=False,
            injection_file=None,
            n_injection=None,
            singularity_image=None,
            local=False,
            X509=os.path.join(self.directory, "X509.txt"),
            queue=1,
            create_summary=False,
            sampler=["nestle"],
            gps_file=None,
            gracedb=None,
            webdir=".",
            email="test@test.com",
            existing_dir=None,
            local_generation=False,
            trigger_time=None,
        )
        self.test_unknown_args = ["--argument", "value"]
        self.inputs = bilby_pipe.main.MainInput(self.test_args, self.test_unknown_args)
        self.inputs.level_A_labels = ["test"]

        self.injection_file = os.path.join(self.outdir, "example_injection_file.h5")
        self.create_injection_args = Namespace(
            outdir=self.outdir,
            label="label",
            prior_file="tests/example_prior.prior",
            n_injection=3,
        )
        ci_inputs = bilby_pipe.create_injections.CreateInjectionInput(
            self.create_injection_args, []
        )
        ci_inputs.create_injection_file(self.injection_file)

    def tearDown(self):
        del self.test_args
        del self.inputs
        shutil.rmtree(self.outdir)

    def test_jobs_creation(self):
        test_args = self.test_args
        test_args.detectors = "H1 L1"
        test_args.coherence_test = True
        inputs = bilby_pipe.main.MainInput(test_args, self.test_unknown_args)
        inputs.level_A_labels = ["test_label"]
        dag = bilby_pipe.main.Dag(inputs)
        JobInput = bilby_pipe.main.JobInput
        expected_jobs = [
            JobInput(
                idx=0,
                meta_label="test_label",
                kwargs=dict(detectors=["H1", "L1"], sampler="nestle"),
            ),
            JobInput(
                idx=0,
                meta_label="test_label",
                kwargs=dict(detectors=["H1"], sampler="nestle"),
            ),
            JobInput(
                idx=0,
                meta_label="test_label",
                kwargs=dict(detectors=["L1"], sampler="nestle"),
            ),
        ]
        self.assertEqual(dag.analysis_jobs_inputs, expected_jobs)

    def test_build_submit(self):
        test_args = self.test_args
        inputs = bilby_pipe.main.MainInput(test_args, self.test_unknown_args)
        inputs.level_A_labels = ["test_label"]
        inputs.submit = True
        bilby_pipe.main.Dag(inputs)

    def test_injection_from_file(self):
        test_args = self.test_args
        test_args.injection = True
        test_args.injection_file = self.injection_file
        inputs = bilby_pipe.main.MainInput(test_args, self.test_unknown_args)
        inputs.level_A_labels = ["test_label"]
        bilby_pipe.main.Dag(inputs)

    def test_injection_from_default_existing_file(self):
        test_args = self.test_args
        test_args.injection = True
        test_args.label = "example"
        inputs = bilby_pipe.main.MainInput(test_args, self.test_unknown_args)
        inputs.level_A_labels = ["test_label"]
        data_dir = os.path.join(self.outdir, "data")
        try:
            os.mkdir(data_dir)
        except FileExistsError:
            pass
        shutil.copyfile(
            self.injection_file, os.path.join(data_dir, "example_injection_file.h5")
        )
        bilby_pipe.main.Dag(inputs)


if __name__ == "__main__":
    unittest.main()
