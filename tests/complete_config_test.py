import os
import shutil
import unittest

import bilby_pipe


class TestMainInput(unittest.TestCase):
    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.outdir = "outdir"
        self.parser = bilby_pipe.main.create_parser()

    def tearDown(self):
        shutil.rmtree(self.outdir)

    def test_complete_config_with_postprocessing(self):
        self.run_test("tests/test_complete_config_with_postprocessing.ini")

    def run_test(self, inifile):

        args_list = [inifile, "--outdir", self.outdir]

        args, unknown_args = self.parser.parse_known_args(args_list)
        inputs = bilby_pipe.main.MainInput(args, unknown_args)

        bilby_pipe.main.write_complete_config_file(self.parser, args, inputs)
        complete_args_list = [
            self.outdir + "/{}_config_complete.ini".format(inputs.label)
        ]
        complete_args, complete_unknown_args = self.parser.parse_known_args(
            complete_args_list
        )
        complete_inputs = bilby_pipe.main.MainInput(
            complete_args, complete_unknown_args
        )

        exclude_keys = ["ini"]

        self.assertEqual(inputs.detectors, complete_inputs.detectors)
        exclude_keys.append("detectors")

        self.assertEqual(inputs.injection_numbers, complete_inputs.injection_numbers)
        exclude_keys.append("injection_numbers")

        self.assertEqual(
            inputs.postprocessing_arguments, complete_inputs.postprocessing_arguments
        )
        exclude_keys.append("postprocessing_arguments")

        self.assertEqual(args.mode_array, complete_args.mode_array[0])
        exclude_keys.append("mode_array")

        self.assertEqual(args.scheduler_module, complete_args.scheduler_module[0])
        exclude_keys.append("scheduler_module")

        mismatched_keys = []
        if args != complete_args:
            for key in vars(args).copy():
                if key not in exclude_keys:
                    val = getattr(args, key)
                    complete_val = getattr(complete_args, key, "N/A")
                    if val != complete_val:
                        print(key, val, type(val), complete_val, type(complete_val))
                        mismatched_keys.append(key)
        self.assertEqual(len(mismatched_keys), 0)


if __name__ == "__main__":
    unittest.main()
