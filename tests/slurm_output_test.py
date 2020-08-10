import os
import shutil
import unittest

import bilby_pipe


class TestSlurm(unittest.TestCase):
    def setUp(self):
        self.outdir = "test_outdir"
        self.known_args_list = [
            "tests/test_main_input.ini",
            "--trigger-time",
            "0",
            "--outdir",
            self.outdir,
            "--scheduler",
            "slurm",
        ]
        self.parser = bilby_pipe.main.create_parser()
        self.args = self.parser.parse_args(self.known_args_list)
        self.inputs = bilby_pipe.main.MainInput(
            *self.parser.parse_known_args(self.known_args_list)
        )

    def tearDown(self):
        if os.path.isdir(self.outdir):
            shutil.rmtree(self.outdir)

    def test_create_slurm_submit(self):
        bilby_pipe.main.generate_dag(self.inputs)
        filename = os.path.join(self.outdir, "submit/slurm_label_master.sh")
        self.assertTrue(os.path.exists(filename))


if __name__ == "__main__":
    unittest.main()
