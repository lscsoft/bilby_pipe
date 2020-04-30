import logging
import os
import shutil
import sys
import unittest

import numpy as np

import bilby
import bilby_pipe
import bilby_pipe.utils
from bilby_pipe.utils import convert_prior_string_input


class TestParseArgs(unittest.TestCase):
    def test_no_command_line_arguments(self):
        input_args = []
        parser = bilby_pipe.bilbyargparser.BilbyArgParser(
            usage=__doc__, ignore_unknown_config_file_keys=True, allow_abbrev=False
        )
        with self.assertRaises(bilby_pipe.utils.BilbyPipeError):
            bilby_pipe.main.parse_args(input_args, parser)


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.outdir = "outdir"
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)

    def tearDown(self):
        logger = logging.getLogger("bilby_pipe")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        shutil.rmtree(self.outdir, ignore_errors=True)

    def test_directory_creation(self):
        directory = self.outdir + "/test-dir"
        self.assertFalse(os.path.isdir(directory))
        bilby_pipe.utils.check_directory_exists_and_if_not_mkdir(directory)
        self.assertTrue(os.path.isdir(directory))

    def test_set_log_level(self):
        bilby_pipe.utils.setup_logger(log_level="info")
        logger = logging.getLogger("bilby_pipe")
        self.assertEqual(logger.level, logging.INFO)

    def test_set_verbose(self):
        sys.argv.append("-v")
        bilby_pipe.utils.setup_logger(log_level="info")
        logger = logging.getLogger("bilby_pipe")
        self.assertEqual(logger.level, logging.DEBUG)
        sys.argv.pop(-1)

    def test_unknown_log_level(self):
        with self.assertRaises(ValueError):
            bilby_pipe.utils.setup_logger(log_level="NOTANERROR")

    def test_write_to_file(self):
        bilby_pipe.utils.setup_logger(outdir=self.outdir, label="TEST")
        self.assertTrue(os.path.isfile("{}/{}.log".format(self.outdir, "TEST")))

    def test_dict_converter(self):
        key = "test"
        cstd = bilby_pipe.utils.convert_string_to_dict
        self.assertEqual(
            cstd("{'a': 10, 'b': 'string', 'c': 1.0}", key),
            dict(a=10, b="string", c=1.0),
        )
        self.assertEqual(
            cstd("{a: 10, b: 'string', c: 1.0}", key), dict(a=10, b="string", c=1.0)
        )
        self.assertEqual(
            cstd("{a: 10, b: string, c: 1.0}", key), dict(a=10, b="string", c=1.0)
        )
        self.assertEqual(
            cstd("{a= 10, b= 'string, c: 1.0}", key), dict(a=10, b="string", c=1.0)
        )
        self.assertEqual(
            cstd("{a= 10, b : 'string', c: '1.0'}", key), dict(a=10, b="string", c=1.0)
        )
        self.assertEqual(
            cstd('{a= 10, b : "string", c: "1.0"}', key), dict(a=10, b="string", c=1.0)
        )
        self.assertEqual(
            cstd('{a=False, b : "True", c: true, "d": "False"}', key),
            dict(a=False, b=True, c=True, d=False),
        )
        self.assertEqual(
            cstd('{a=+1, b : "+1", c: -1, "d": "-1"}', key), dict(a=1, b=1, c=-1, d=-1)
        )
        self.assertEqual(
            cstd('{a=+1.6, b : "+1.6", c: -1.6, "d": "-1.6"}', key),
            dict(a=1.6, b=1.6, c=-1.6, d=-1.6),
        )
        self.assertEqual(
            cstd('{path=/path/to/file.txt, path_with_quotes : "/path/to/file.txt"}'),
            dict(path="/path/to/file.txt", path_with_quotes="/path/to/file.txt"),
        )
        self.assertEqual(
            cstd(
                '{path=../path/to/file.txt, path_with_quotes : "../path/to/file.txt"}'
            ),
            dict(path="../path/to/file.txt", path_with_quotes="../path/to/file.txt"),
        )
        self.assertEqual(
            cstd('{int=3, int_with_quotes : "1"}'), dict(int=3, int_with_quotes=1)
        )
        self.assertEqual(
            cstd('{float=3.0, float_with_quotes : "1.0"}'),
            dict(float=3.0, float_with_quotes=1.0),
        )
        self.assertEqual(
            cstd("{float=3.0, labels=[Online, Online]}"),
            dict(float=3.0, labels=["Online", "Online"]),
        )
        self.assertEqual(
            cstd('{float=3.0, labels=["Online", "Online"]}'),
            dict(float=3.0, labels=["Online", "Online"]),
        )
        self.assertTrue(isinstance(cstd("{float=3.0}")["float"], float))
        self.assertTrue(isinstance(cstd("{float=3.1}")["float"], float))
        self.assertTrue(isinstance(cstd("{int=3}")["int"], int))

        # Tested nested dictionaries
        self.assertEqual(
            cstd('{a={a=1, b : "-1", c=test}}', key), dict(a=dict(a=1, b=-1, c="test"))
        )

    def test_list_of_lists_converter(self):
        cstll = bilby_pipe.utils.convert_string_to_list
        # Check list of ints
        self.assertEqual(cstll("[1, 2, 3]"), [1, 2, 3])
        self.assertEqual(cstll("['1', '2', '3']"), [1, 2, 3])

        # Check lists of strings and ints
        self.assertEqual(cstll("['1', 'a', '3']"), [1, "a", 3])
        self.assertEqual(cstll("['1', a, '3']"), [1, "a", 3])

        # Check lists of lists of ints
        self.assertEqual(cstll("[[1, 2], [2, 3]]"), [[1, 2], [2, 3]])
        self.assertEqual(cstll("[['1', '2'], [2, 3]]"), [[1, 2], [2, 3]])
        self.assertEqual(cstll("[[[1], [2]], [2, 3]]"), [[[1], [2]], [2, 3]])

    def test_convert_detectors_input(self):
        self.assertEqual(["H1"], bilby_pipe.utils.convert_detectors_input("H1"))
        self.assertEqual(["H1"], bilby_pipe.utils.convert_detectors_input("[H1]"))
        self.assertEqual(["H1"], bilby_pipe.utils.convert_detectors_input("'H1'"))
        self.assertEqual(["H1"], bilby_pipe.utils.convert_detectors_input('"H1"'))
        self.assertEqual(
            ["H1", "L1"], bilby_pipe.utils.convert_detectors_input("H1 L1")
        )
        self.assertEqual(
            ["H1", "L1"], bilby_pipe.utils.convert_detectors_input("[H1 L1]")
        )
        self.assertEqual(
            ["H1", "L1"], bilby_pipe.utils.convert_detectors_input("['H1' 'L1']")
        )
        self.assertEqual(
            ["H1", "L1"], bilby_pipe.utils.convert_detectors_input('["H1" "L1"]')
        )
        self.assertEqual(
            ["H1", "L1"], bilby_pipe.utils.convert_detectors_input("['H1', 'L1']")
        )
        self.assertEqual(
            ["H1", "L1"], bilby_pipe.utils.convert_detectors_input('["H1", "L1"]')
        )
        self.assertEqual(
            ["H1", "L1"], bilby_pipe.utils.convert_detectors_input("'H1', 'L1'")
        )
        self.assertEqual(
            ["H1", "L1"], bilby_pipe.utils.convert_detectors_input('"H1", "L1"')
        )
        self.assertEqual(
            ["H1", "L1"], bilby_pipe.utils.convert_detectors_input('"L1", "H1"')
        )
        self.assertEqual(
            ["H1", "L1"], bilby_pipe.utils.convert_detectors_input(["L1", "H1"])
        )

    def test_convert_prior_string_input_simpe(self):
        self.assertEqual(dict(a="1", b="2"), convert_prior_string_input("{a: 1, b:2}"))

    def test_convert_prior_string_input_standard(self):
        check = dict(a="Uniform(name='ra',minimum=0,maximum=2*np.pi)", b="2")
        out = convert_prior_string_input(
            "{a: Uniform(name='ra', minimum=0, maximum=2*np.pi), b=2}"
        )
        self.assertEqual(out, check)
        bbh_prior = bilby.gw.prior.BBHPriorDict(out)
        self.assertEqual(
            bbh_prior["a"],
            bilby.core.prior.Uniform(name="ra", minimum=0, maximum=2 * np.pi),
        )

    def test_convert_prior_string_input_nested(self):
        otstr = "bilby.gw.prior.AlignedSpin(name='chi_1',a_prior=bilby.core.prior.Uniform(minimum=0,maximum=0.8))"
        instr = (
            "{chi_1: bilby.gw.prior.AlignedSpin(name='chi_1',"
            " a_prior=bilby.core.prior.Uniform(minimum=0, maximum=0.8))}"
        )
        out = convert_prior_string_input(instr)
        self.assertEqual(dict(chi_1=otstr), out)
        self.assertEqual(
            eval(out["chi_1"]),
            bilby.gw.prior.AlignedSpin(
                name="chi_1", a_prior=bilby.core.prior.Uniform(minimum=0, maximum=0.8)
            ),
        )


if __name__ == "__main__":
    unittest.main()
