import glob
import os
import shutil
import unittest

import bilby_pipe


class TestCustomDir(unittest.TestCase):
    def setUp(self):
        self.init_dir = "tests/initdir"
        self.outdir = os.path.join(self.init_dir, "outdir")
        self.webdir = os.path.join(self.outdir, "results_page")
        self.logdirs = os.path.join(self.outdir, "log_*")

        os.makedirs(self.init_dir, exist_ok=True)
        self.parser = bilby_pipe.main.create_parser()
        self.ini = os.path.join(self.init_dir, "test_custom_dir.ini")

    def tearDown(self):
        shutil.rmtree(self.init_dir)

    def generate_ini(self, extra_lines=[]):
        """Generates an ini file"""
        f = open(self.ini, mode="w")
        starting_lines = [
            "detectors = [H1, L1]",
            f"outdir = {self.outdir}",
            "accounting = accounting.group",
            "submit=True",
            "trigger-time=0",
        ]
        lines = starting_lines + extra_lines
        for l in lines:
            f.write(l + "\n")
        f.close()

    def test_default_dir_structure(self):
        self.generate_ini()
        args = self.parser.parse_args([self.ini])
        inputs = bilby_pipe.main.MainInput(args, [])
        bilby_pipe.main.write_complete_config_file(self.parser, args, inputs)
        bilby_pipe.main.generate_dag(inputs)

        for d in [self.webdir] + glob.glob(self.logdirs):
            self.assertTrue(os.path.isdir(d), f"{d} is not a dir")

    def test_custom_dir_structure(self):
        new_logdir = os.path.join(self.init_dir, "new_logdir")
        new_webdir = os.path.join(self.init_dir, "new_webdir")
        self.generate_ini([f"log-directory={new_logdir}", f"webdir={new_webdir}"])
        args = self.parser.parse_args([self.ini])
        inputs = bilby_pipe.main.MainInput(args, [])
        bilby_pipe.main.write_complete_config_file(self.parser, args, inputs)
        bilby_pipe.main.generate_dag(inputs)

        for d in [new_webdir] + glob.glob(new_logdir + "log_*"):
            self.assertTrue(os.path.isdir(d), f"{d} is not a dir")

        for d in [self.webdir] + glob.glob(self.logdirs):
            self.assertFalse(os.path.isdir(d), f"{d} is a dir")
