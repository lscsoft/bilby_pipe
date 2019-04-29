import unittest

import bilby_pipe


class TestDagCommandLine(unittest.TestCase):
    def setUp(self):
        self.default_args = ["tests/test_dag_ini_file.ini"]
        self.parser = bilby_pipe.main.create_main_parser()

    def tearDown(self):
        pass

    def test_ini_fail(self):
        args = ["not_a_file"]
        with self.assertRaises(SystemExit):
            bilby_pipe.main.parse_args(args, self.parser)

    def test_ini(self):
        args, unknown_args = bilby_pipe.main.parse_args(self.default_args, self.parser)
        self.assertEqual(args.ini, self.default_args[0])
        self.assertEqual(args.accounting, "test.test")

    def test_empty_unknown_args(self):
        _, unknown_args = bilby_pipe.main.parse_args(self.default_args, self.parser)
        self.assertEqual(unknown_args, [])

    def test_unknown_args(self):
        expected_unknown_args = ["--other", "thing"]
        args = self.default_args + expected_unknown_args
        args, unknown_args = bilby_pipe.main.parse_args(args, self.parser)
        self.assertEqual(unknown_args, expected_unknown_args)


# class TestScriptHelperCommandLine(unittest.TestCase):
#
#     def setUp(self):
#         self.default_args = ['--ini', 'tests/test_script_helper_ini_file.ini']
#         self.parser = bilby_pipe.script_helper.create_default_parser()
#
#     def tearDown(self):
#         pass
#
#     def test_detectors_ini(self):
#         args_list = self.default_args.copy()
#         parsed_args = self.parser.parse_args(args_list)
#         self.assertEqual(type(parsed_args.detectors), list)
#         self.assertEqual(parsed_args.detectors, ['H1', 'L1'])
#
#     def test_detectors_command_line(self):
#         args_list = self.default_args.copy()
#         args_list.append('--detectors')
#         args_list.append('H1')
#         args_list.append('--detectors')
#         args_list.append('L1')
#         parsed_args = self.parser.parse_args(args_list)
#         self.assertEqual(type(parsed_args.detectors), list)
#         self.assertEqual(parsed_args.detectors, ['H1', 'L1'])
#
#     def test_sampler_kwargs_ini(self):
#         args_list = self.default_args.copy()
#         parsed_args = self.parser.parse_args(args_list)
#         self.assertEqual(type(parsed_args.sampler_kwargs), str)
#         self.assertEqual("{'a': 1, 'b': 2}", parsed_args.sampler_kwargs)
#
#     def test_sampler_kwargs_command_line(self):
#         args_list = self.default_args.copy()
#         args_list.append('--sampler-kwargs')
#         args_list.append("{'a': 1, 'b': 2}")
#         parsed_args = self.parser.parse_args(args_list)
#         self.assertEqual(type(parsed_args.sampler_kwargs), str)
#         self.assertEqual("{'a': 1, 'b': 2}", parsed_args.sampler_kwargs)
#
#     def test_calbration_ini(self):
#         args_list = self.default_args.copy()
#         args_list.append('--calibration')
#         args_list.append('4')
#         parsed_args = self.parser.parse_args(args_list)
#         self.assertEqual(parsed_args.calibration, 4)
#
#     def test_duration_ini(self):
#         args_list = self.default_args.copy()
#         args_list.append('--duration')
#         args_list.append('4')
#         parsed_args = self.parser.parse_args(args_list)
#         self.assertEqual(parsed_args.duration, 4)


if __name__ == "__main__":
    unittest.main()
