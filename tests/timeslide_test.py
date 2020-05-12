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
        self.outdir = "tests/timeslide_outdir"
        os.makedirs(self.outdir, exist_ok=True)
        self.parser = bilby_pipe.main.create_parser()
        self.ini = os.path.join(self.outdir, "test_timeslide.ini")
        self.gps_file = "tests/gps_file_for_timeslides.txt"
        self.timeslide_file = "tests/timeslides.txt"

    def tearDown(self):
        shutil.rmtree(self.outdir)

    def get_args_from_ini(self):
        inputs = bilby_pipe.main.MainInput(self.parser.parse_args([self.ini]), [])
        return inputs

    def test_timeslide_file_parsed_into_timeslide_dictionary(self):
        self.generate_ini(self.ini)
        inputs = self.get_args_from_ini()
        # Setting GPS and timeslide into the input object
        inputs.gps_file = self.gps_file
        inputs.timeslide_file = self.timeslide_file
        # Checking that the input object parses the timeslide into a dict
        self.assertIsInstance(inputs.timeslides, dict)
        # Checking contents of dict matches up what is expected
        correct_timeslides = {"H1": [-50, 20, -100], "L1": [50, -20, 100]}
        for det in inputs.timeslides.keys():
            self.assertEqual(len(inputs.timeslides[det]), 3)
            for idx, i in enumerate(inputs.timeslides[det]):
                self.assertEqual(i, correct_timeslides[det][idx])

    def test_error_thrown_for_non_existant_timeslide_file(self):
        self.generate_ini(self.ini)
        inputs = self.get_args_from_ini()
        # checks that timeslide parser throws an error if the file is not found
        with self.assertRaises(FileNotFoundError):
            inputs.timeslide_file = "not a file"
        # checks that error thrown when no timslide dict set
        with self.assertRaises(BilbyPipeError):
            inputs.get_timeslide_dict(0)

    def test_number_of_columns_in_timeslide_file_matches_num_detectors(self):
        # generate a gps time file, timeslide file, ini file
        n_rows, n_det = 5, 2
        timeslide_f = os.path.join(self.outdir, "fake_timeslides.txt")
        gps_f = os.path.join(self.outdir, "fake_gps.txt")
        self.generate_gps_and_timeslide_files(timeslide_f, gps_f, n_rows, n_det)
        self.generate_ini(
            self.ini, extra_lines=[f"gps-file={gps_f}", f"timeslide-file={timeslide_f}"]
        )
        inputs = self.get_args_from_ini()
        self.assertEqual(len(inputs.detectors), n_det, "num detectors not matching")

        # check if parsed contents of file matches what we expect
        correct_list = {"H1": np.zeros(n_rows), "L1": np.ones(n_rows)}
        for det in inputs.timeslides.keys():
            self.assertEqual(len(inputs.timeslides[det]), n_rows, "#rows not matching")
            for idx, i in enumerate(inputs.timeslides[det]):
                self.assertEqual(i, correct_list[det][idx], "tslide val not matching")

        # check if an error is raised with incorrect number of columns
        with self.assertRaises(BilbyPipeError):
            self.generate_gps_and_timeslide_files(timeslide_f, gps_f, n_rows, 1)
            inputs.timeslide_file = timeslide_f

    @mock.patch("bilby_pipe.data_generation.logger")
    def test_data_generation_data_get_with_timeslide_values(self, mock_logger):
        """Test timeslide values configured in bilby_pipe.data_generation._get_data()
        """
        gps_times = np.loadtxt(self.gps_file)
        timeslides = np.loadtxt(self.timeslide_file)
        idx = 0
        self.generate_ini(
            self.ini,
            extra_lines=[
                f"gps-file={self.gps_file}",
                f"timeslide-file={self.timeslide_file}\n",
                f"idx={idx}",
                f"trigger-time={gps_times[idx] - 2}",
                "channel-dict={'H1': 'GDS-CALIB_STRAIN', 'L1': 'GDS-CALIB_STRAIN'}",
                "data-dict={'H1':tests/DATA/strain.hdf5, 'L1':tests/DATA/strain.hdf5}",
                "psd-dict={'H1':tests/DATA/psd.txt, 'L1':tests/DATA/psd.txt}",
                "psd-duration=4",
                "create-plots=True",
            ],
        )
        parser = create_generation_parser()
        inputs = DataGenerationInput(*bilby_pipe.main.parse_args([self.ini], parser))
        timeslide_dict = inputs.timeslide_dict
        expected_dict = dict(H1=timeslides[idx][0], L1=timeslides[idx][1])
        self.assertDictEqual(timeslide_dict, expected_dict)

        logs = [ll.args[0] for ll in mock_logger.info.call_args_list]
        t_log = "Applying timeshift of {tval}. Time range {t0} - {t1} => {nt0} - {nt1}"

        for ifo_num, ifo in enumerate(inputs.interferometers):
            # make sure timeslide was applied
            tval = timeslides[idx][ifo_num]
            t0 = gps_times[idx] - inputs.duration
            t1 = gps_times[idx]
            nt0, nt1 = t0 + tval, t1 + tval
            ifo_log = t_log.format(tval=tval, t0=t0, t1=t1, nt0=nt0, nt1=nt1)
            self.assertTrue(ifo_log in logs, msg=f"log '{ifo_log}' not in {logs}")

            # Check that the ifo's start time is reset to match after timeslides applied
            self.assertEqual(ifo.strain_data.start_time, t0)

    def generate_ini(self, filepath, extra_lines=[]):
        """Generates an ini file"""
        f = open(filepath, mode="w")
        starting_lines = [
            "detectors = [H1, L1]",
            f"outdir = {self.outdir}",
            "accounting = accounting.group" "submit=True",
        ]
        lines = starting_lines + extra_lines
        for ll in lines:
            f.write(ll + "\n")
        f.close()

    def generate_gps_and_timeslide_files(
        self, timeslide_filename, gps_filename, num_rows, num_detectors
    ):
        """ Generates a gps and timeslide file

        gps times : [0, 0, 0, 0, 0]
        timeslide : [ [0, 1], [0, 1] ...]

        """
        # multi-colum timeslide file
        columns_of_vals = np.zeros((num_rows, num_detectors))
        if num_detectors > 1:
            columns_of_vals[:, 1] += 1
        np.savetxt(timeslide_filename, columns_of_vals, delimiter="\t")
        # one column gps file
        one_column_of_vals = np.zeros(num_rows)
        np.savetxt(gps_filename, one_column_of_vals, delimiter="\t")
