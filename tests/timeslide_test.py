import os
import shutil
import unittest

import mock
import numpy as np

import bilby_pipe
from bilby_pipe.data_generation import DataGenerationInput, create_generation_parser
from bilby_pipe.utils import BilbyPipeError


class TestTimeslide(unittest.TestCase):
    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.outdir = "outdir"
        self.known_args_list = [
            "tests/test_timeslide.ini",
            "--submit",
            "--outdir",
            self.outdir,
        ]
        self.unknown_args_list = ["--argument", "value"]
        self.all_args_list = self.known_args_list + self.unknown_args_list
        self.parser = bilby_pipe.main.create_parser()
        self.args = self.parser.parse_args(self.known_args_list)
        self.inputs = bilby_pipe.main.MainInput(
            *self.parser.parse_known_args(self.all_args_list)
        )

        self.gps_file = "tests/gps_file_for_timeslides.txt"
        self.timeslide_file = "tests/timeslides.txt"

    def tearDown(self):
        shutil.rmtree(self.outdir)
        del self.args
        del self.inputs

    def test_timeslide_file_parser(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        inputs.gps_file = self.gps_file
        inputs.timeslide_file = self.timeslide_file
        self.assertIsInstance(inputs.timeslides, dict)
        self.assertEqual(
            inputs.timeslides.keys(), {d: [] for d in inputs.detectors}.keys()
        )

    def test_timeslide_file_fake(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)

        with self.assertRaises(FileNotFoundError):
            inputs.timeslide_file = "not a file"

        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        with self.assertRaises(FileNotFoundError):
            inputs.timeslide_file = "fakepath.txt"

    def test_correct_number_of_columns_in_file(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        self.assertEqual(len(inputs.detectors), 2, "num detectors")

        valid_timeslide_file = os.path.join(self.outdir, "fake_timeslides_file.txt")
        valid_gps_file = os.path.join(self.outdir, "fake_gps_file.txt")
        one_column_of_vals = np.zeros(5)
        two_columns_of_vals = np.ones((5, 2))
        two_columns_of_vals[:, 1] += 1

        np.savetxt(valid_timeslide_file, two_columns_of_vals, delimiter="\t")
        np.savetxt(valid_gps_file, one_column_of_vals, delimiter="\t")

        inputs.gps_file = valid_gps_file
        inputs.timeslide_file = valid_timeslide_file

        correct_list = {
            "H1": two_columns_of_vals[:, 0],
            "L1": two_columns_of_vals[:, 1],
        }
        for det in inputs.timeslides.keys():
            self.assertEqual(len(inputs.timeslides[det]), 5)
            for idx, i in enumerate(inputs.timeslides[det]):
                self.assertEqual(i, correct_list[det][idx])
        pass

    def test_incorrect_number_of_columns_in_file(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        self.assertEqual(len(inputs.detectors), 2)

        one_column_of_vals = np.zeros(5)
        valid_gps_file = os.path.join(self.outdir, "fake_gps_file.txt")
        np.savetxt(valid_gps_file, one_column_of_vals, delimiter="\t")
        inputs.gps_file = valid_gps_file

        # invalid number of columns in timeslide file
        invalid_timeslides_file = os.path.join(self.outdir, "fake_timeslides_file.txt")
        np.savetxt(invalid_timeslides_file, one_column_of_vals, delimiter="\t")
        with self.assertRaises(BilbyPipeError):
            inputs.timeslide_file = invalid_timeslides_file

        # invalid number of rows in timeslide file
        np.savetxt(invalid_timeslides_file, np.zeros(3), delimiter="\t")
        with self.assertRaises(BilbyPipeError):
            inputs.timeslide_file = invalid_timeslides_file

    def test_timeslide_file(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        inputs.gps_file = self.gps_file
        inputs.timeslide_file = self.timeslide_file
        self.assertIsInstance(inputs.get_timeslide_dict(idx=0), dict)
        self.assertIsInstance(inputs.get_timeslide_dict(idx=1), dict)
        self.assertIsInstance(inputs.get_timeslide_dict(idx=2), dict)
        with self.assertRaises(BilbyPipeError):
            inputs.get_timeslide_dict(idx=3)
        self.assertTrue(
            all(
                len(ifo_timeslides) == 3
                for ifo_timeslides in inputs.timeslides.values()
            )
        )

    def test_timeslide_parser(self):
        inputs = bilby_pipe.main.MainInput(self.args, self.unknown_args_list)
        with self.assertRaises(BilbyPipeError):
            inputs.get_timeslide_dict(0)

        args_list = ["tests/test_timeslide_2.ini"]
        parser = bilby_pipe.main.create_parser()
        inputs = bilby_pipe.main.MainInput(*parser.parse_known_args(args_list))
        timeslide_val = inputs.get_timeslide_dict(0)

        correct_timeslides = {"H1": [-1, 20, -100], "L1": [1, -20, 100]}
        for det in inputs.timeslides.keys():
            self.assertEqual(len(inputs.timeslides[det]), 3)
            for idx, i in enumerate(inputs.timeslides[det]):
                self.assertEqual(i, correct_timeslides[det][idx])

        self.assertIsNotNone(timeslide_val)
        self.assertIsInstance(timeslide_val, dict)
        self.assertDictEqual(timeslide_val, {"H1": -1, "L1": 1})

        with self.assertRaises(BilbyPipeError):
            inputs.get_timeslide_dict(10000)

    @mock.patch("gwpy.timeseries.TimeSeries.fetch_open_data")
    @mock.patch("bilby_pipe.data_generation.DataGenerationInput._is_gwpy_data_good")
    def test_data_get(self, data_quality_method, fetch_open_data_method):
        """Test timeslide values being properly set in function call to gwpy.

        Parameters
        ----------
        data_quality_method: mock the data_quality_method to return True
        fetch_open_data_method: mock the fetch_open_data_method

        """
        args_list = [
            "--ini",
            "tests/test_timeslide_2.ini",
            "--outdir",
            self.outdir,
            "--trigger-time",
            "1126258462",
            "idx",
            "0",
            "--data-label",
            "TEST",
        ]
        parser = create_generation_parser()

        # loading data so we don't have to deal with gwpy's slow fetch_data method
        from bilby_pipe.utils import DataDump

        d = DataDump.from_pickle("tests/gwpy_data.pickle")
        timeseries = d.interferometers[0].strain_data.to_gwpy_timeseries()

        fetch_open_data_method.return_value = timeseries
        data_quality_method.return_value = True
        self.inputs = DataGenerationInput(
            *bilby_pipe.main.parse_args(args_list, parser)
        )
        timeslide_dict = self.inputs.timeslide_dict
        self.assertIsInstance(timeslide_dict, dict)

        t0 = self.inputs.start_time
        t1 = t0 + self.inputs.duration

        t0_psd = t0 - 128
        t1_psd = t0

        for det, timeslide_val in timeslide_dict.items():
            fetch_open_data_method.assert_any_call(
                det, t0 + timeslide_val, t1 + timeslide_val
            )  # SIGNAL
            fetch_open_data_method.assert_any_call(
                det, t0_psd + timeslide_val, t1_psd + timeslide_val
            )  # PSD
