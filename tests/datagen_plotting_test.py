import unittest
import shutil
import mock
import os
import bilby_pipe

import gwpy

from bilby_pipe.data_generation import DataGenerationInput, create_generation_parser
from bilby_pipe.plotting_utils import strain_spectogram_plot


class TestDataGenerationPlotting(unittest.TestCase):
    def setUp(self):
        self.outdir = "test_outdir_plots"
        self.default_args_list = [
            "--ini",
            "tests/test_data_generation.ini",
            "--outdir",
            self.outdir,
            "--data-label",
            "TEST",
        ]
        self.strain = gwpy.timeseries.TimeSeries.read("tests/strain.hdf5")
        self.psd = gwpy.timeseries.TimeSeries.read("tests/psd.hdf5")

    def tearDown(self):
        shutil.rmtree(self.outdir)

    def test_psd_plot(self):
        os.makedirs(self.outdir, exist_ok=True)
        strain_spectogram_plot(det="L1", data=self.psd, data_directory=self.outdir)

    @mock.patch("bilby_pipe.data_generation.DataGenerationInput._is_gwpy_data_good")
    @mock.patch("gwpy.timeseries.TimeSeries.fetch_open_data")
    def test_plot_data(self, data_get, is_data_good):
        data_get.side_effect = [self.strain, self.psd]
        is_data_good.return_value = True

        args_list = [
            "--ini",
            "tests/test_timeslide.ini",
            "--detectors",
            "[H1]",
            "--channel-dict",
            "{'H1': 'GDS-CALIB_STRAIN',}",
            "--outdir",
            self.outdir,
            "--trigger-time",
            "1126259462.4",
            "idx",
            "0",
            "--data-label",
            "TEST",
            "--label",
            "TEST",
            "--create-plots",
        ]
        parser = create_generation_parser()

        plot_filenames = [
            "H1_TEST_D4_data.png",
            "H1_TEST_D128_data.png",
            "H1_TEST_frequency_domain_data.png",
        ]
        plot_dir = os.path.join(self.outdir, "data")
        plot_filenames = [os.path.join(plot_dir, p) for p in plot_filenames]

        DataGenerationInput(*bilby_pipe.main.parse_args(args_list, parser))
        for p in plot_filenames:
            self.assertTrue(os.path.isfile(p), p)
