import os
import shutil
import unittest
from argparse import Namespace

import bilby_pipe


class TestSlurm(unittest.TestCase):
    def setUp(self):
        self.outdir = "test_outdir"
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.test_args = Namespace(
            ini="tests/test_dag_ini_file.ini",
            submit=False,
            online_pe=False,
            outdir=self.outdir,
            label="label",
            accounting="accounting.group",
            detectors="H1",
            coherence_test=False,
            n_parallel=1,
            injection=False,
            injection_file=None,
            injection_dict=None,
            injection_waveform_approximant=None,
            n_injection=None,
            injection_numbers=None,
            singularity_image=None,
            local=False,
            queue=1,
            create_summary=False,
            sampler=["nestle"],
            ignore_gwpy_data_quality_check=True,
            gps_file=None,
            gps_tuple=None,
            timeslide_file=None,
            webdir=".",
            email="test@test.com",
            existing_dir=None,
            local_generation=False,
            local_plot=False,
            trigger_time=0,
            deltaT=0.2,
            waveform_approximant="IMRPhenomPV2",
            request_memory="4 GB",
            request_memory_generation="4 GB",
            request_cpus=1,
            generation_seed=None,
            transfer_files=True,
            prior_file="4s",
            prior_dict=None,
            default_prior="BBHPriorDict",
            postprocessing_executable=None,
            postprocessing_arguments=None,
            summarypages_arguments=None,
            scheduler="slurm",
            scheduler_args="account=myaccount partition=mypartition",
            scheduler_module=None,
            scheduler_env=None,
            data_dict=None,
            create_plots=False,
            likelihood_type=None,
            duration=4,
            post_trigger_duration=2,
            gaussian_noise=True,
            n_simulation=1,
            log_directory=None,
            osg=True,
        )
        self.test_unknown_args = ["--argument", "value"]
        self.inputs = bilby_pipe.main.MainInput(self.test_args, self.test_unknown_args)

        self.injection_file = os.path.join(self.outdir, "example_injection_file.h5")

    def tearDown(self):
        del self.test_args
        del self.inputs
        shutil.rmtree(self.outdir)

    def test_create_slurm_submit(self):
        test_args = self.test_args
        inputs = bilby_pipe.main.MainInput(test_args, self.test_unknown_args)
        bilby_pipe.main.generate_dag(inputs)
        filename = os.path.join(self.outdir, "submit/label_master_slurm.sh")
        self.assertTrue(os.path.exists(filename))


if __name__ == "__main__":
    unittest.main()
