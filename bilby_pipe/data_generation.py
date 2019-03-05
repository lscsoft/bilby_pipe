#!/usr/bin/env python
"""
Module containing the tools for data generation
"""
from __future__ import division, print_function

import sys
import urllib
import urllib.request

import matplotlib
import numpy as np
import gwpy

matplotlib.use("agg")  # noqa
import bilby
from bilby.gw.detector import PowerSpectralDensity

from bilby_pipe.utils import logger, BilbyPipeError
from bilby_pipe.main import DataDump, parse_args
from bilby_pipe.input import Input
from bilby_pipe.parser import create_parser

try:
    import nds2  # noqa
except ImportError:
    logger.warning(
        "You do not have nds2 (python-nds2-client) installed. You may "
        " experience problems accessing interferometer data."
    )

try:
    import LDAStools  # noqa
except ImportError:
    logger.warning(
        "You do not have LDAStools (python-ldas-tools-framecpp) installed."
        " You may experience problems accessing interferometer data."
    )


class DataGenerationInput(Input):
    """ Handles user-input and creation of intermediate interferometer list

    Parameters
    ----------
    parser: configargparse.ArgParser, optional
        The parser containing the command line / ini file inputs
    args_list: list, optional
        A list of the arguments to parse. Defauts to `sys.argv[1:]`
    create_data: bool
        If false, no data is generated (used for testing)

    """

    def __init__(self, args, unknown_args, create_data=True):

        np.random.seed(args.generation_seed)

        logger.info("Command line arguments: {}".format(args))
        logger.info("Unknown command line arguments: {}".format(unknown_args))
        self.meta_data = dict(
            command_line_args=args,
            unknown_command_line_args=unknown_args,
            injection_parameters=None,
        )
        self.ini = args.ini
        self.cluster = args.cluster
        self.process = args.process
        self.idx = args.idx
        self.detectors = args.detectors
        self.channel_type = args.channel_type
        self.duration = args.duration
        self.post_trigger_duration = args.post_trigger_duration
        self.sampling_frequency = args.sampling_frequency
        self.psd_length = args.psd_length
        self.psd_fractional_overlap = args.psd_fractional_overlap
        self.psd_start_time = args.psd_start_time
        self.psd_method = args.psd_method
        self.psd_files = args.psd_files
        self.minimum_frequency = args.minimum_frequency
        self.outdir = args.outdir
        self.label = args.label
        self.frequency_domain_source_model = args.frequency_domain_source_model
        self.waveform_approximant = args.waveform_approximant
        self.reference_frequency = args.reference_frequency
        if create_data:
            self.create_data(args)

    def create_data(self, args):
        """ Function to iterarate through data generation method

        Note, the data methods are mutually exclusive and only one can given to
        the parser.

        Parameters
        ----------
        args: Namespace
            Input arguments

        Raises
        ------
        BilbyPipeError:
            If no data is generated

        """

        self.data_set = False
        # The following are all mutually exclusive methods to set the data
        if args.injection_file is not None:
            self.injection_file = args.injection_file
            self._set_interferometers_from_injection()
        elif self.data_set is False and args.gracedb is not None:
            self.gracedb = args.gracedb
            self._set_interferometers_from_data()
        elif self.data_set is False and args.gps_file is not None:
            self.gps_file = args.gps_file
            self._set_interferometers_from_data()
        elif self.data_set is False and args.trigger_time is not None:
            self.trigger_time = args.trigger_time
            self._set_interferometers_from_data()

        if self.data_set is False:
            raise BilbyPipeError("No data setting method provided")

    @property
    def cluster(self):
        return self._cluster

    @cluster.setter
    def cluster(self, cluster):
        try:
            self._cluster = int(cluster)
        except (ValueError, TypeError):
            logger.debug("Unable to convert input `cluster` to type int")
            self._cluster = cluster

    @property
    def process(self):
        return self._process

    @process.setter
    def process(self, process):
        try:
            self._process = int(process)
        except (ValueError, TypeError):
            logger.debug("Unable to convert input `process` to type int")
            self._process = process

    @property
    def psd_length(self):
        """ Integer number of durations to use for generating the PSD """
        return self._psd_length

    @psd_length.setter
    def psd_length(self, psd_length):
        if isinstance(psd_length, int):
            self._psd_length = psd_length
            self.psd_duration = psd_length * self.duration
            logger.info(
                "PSD duration set to {}s, {}x the duration {}s".format(
                    self.psd_duration, psd_length, self.duration
                )
            )
        else:
            raise BilbyPipeError("Unable to set the psd length")

    @property
    def psd_start_time(self):
        """ The PSD start time relative to segment start time """
        if self._psd_start_time is not None:
            return self._psd_start_time
        elif self.trigger_time is not None:
            psd_start_time = -self.psd_duration
            logger.info("Using default PSD start time {}".format(psd_start_time))
            return psd_start_time
        else:
            raise BilbyPipeError("PSD start time not set")

    @psd_start_time.setter
    def psd_start_time(self, psd_start_time):
        if psd_start_time is None:
            self._psd_start_time = None
        else:
            self._psd_start_time = psd_start_time
            logger.info(
                "PSD start-time set to {} relative to segment start time".format(
                    self._psd_start_time
                )
            )

    @property
    def minimum_frequency(self):
        return self._minimum_frequency

    @minimum_frequency.setter
    def minimum_frequency(self, minimum_frequency):
        self._minimum_frequency = float(minimum_frequency)

    @property
    def parameter_conversion(self):
        if "binary_neutron_star" in self.frequency_domain_source_model:
            return bilby.gw.conversion.convert_to_lal_binary_neutron_star_parameters
        elif "binary_black_hole" in self.frequency_domain_source_model:
            return bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters
        else:
            return None

    @property
    def detectors(self):
        """ A list of the detectors to search over, e.g., ['H1', 'L1'] """
        return self._detectors

    @detectors.setter
    def detectors(self, detectors):
        """ Handles various types of user input """
        if isinstance(detectors, list):
            if len(detectors) == 1:
                det_list = self._convert_string_to_list(detectors[0])
            else:
                det_list = detectors
        else:
            raise ValueError("Input `detectors` = {} not understood".format(detectors))

        det_list.sort()
        det_list = [det.upper() for det in det_list]
        self._detectors = det_list

    @property
    def trigger_time(self):
        return self._trigger_time

    @trigger_time.setter
    def trigger_time(self, trigger_time):
        self._trigger_time = trigger_time

    @property
    def gracedb(self):
        """ The gracedb of the candidate """
        return self._gracedb

    @gracedb.setter
    def gracedb(self, gracedb):
        """ Set the gracedb ID

        At setting, will load the json candidate data and path to the frame
        cache file.

        Parameters
        ----------
        gracedb: str
            The gracedb UID string

        """
        if gracedb is None:
            self._gracedb = None
        else:
            logger.info("Setting gracedb id to {}".format(gracedb))
            self.test_connection()
            candidate = bilby.gw.utils.gracedb_to_json(
                gracedb, outdir=self.data_directory
            )
            self.meta_data["gracedb_candidate"] = candidate
            self._gracedb = gracedb
            self.trigger_time = candidate["gpstime"]

    def test_connection(self):
        """ A generic test to see if the network is reachable """
        try:
            urllib.request.urlopen("https://google.com", timeout=0.1)
        except urllib.error.URLError:
            raise BilbyPipeError(
                "It appears you are not connected to a network and so won't be "
                "able to interface with GraceDB. You may wish to specify the "
                " local-generation argument either in the configuration file "
                "or by passing the --local-generation command line argument"
            )

    def _parse_gps_file(self):
        """ Reads in the GPS file selects the required time and set the trigger time

        Note, the gps_file setter method is defined in bilby_pipe.input
        """
        gps_start_times = self.read_gps_file()
        self.start_time = gps_start_times[self.idx]
        self.trigger_time = self.start_time + self.duration / 2.0

    def _set_interferometers_from_injection(self):
        """ Method to generate the interferometers data from an injection """

        self.injection_parameters = self.injection_df.iloc[self.idx].to_dict()
        self.meta_data["injection_parameters"] = self.injection_parameters
        self.trigger_time = self.injection_parameters["geocent_time"]

        waveform_arguments = dict(
            waveform_approximant=self.waveform_approximant,
            reference_frequency=self.reference_frequency,
            minimum_frequency=self.minimum_frequency,
        )

        waveform_generator = bilby.gw.WaveformGenerator(
            duration=self.duration,
            sampling_frequency=self.sampling_frequency,
            frequency_domain_source_model=self.bilby_frequency_domain_source_model,
            parameter_conversion=self.parameter_conversion,
            waveform_arguments=waveform_arguments,
        )

        ifos = bilby.gw.detector.InterferometerList(self.detectors)

        if self.psd_files is not None:
            for ifo in ifos:
                if ifo.name in self.psd_file_dict.keys():
                    self._set_psd_from_file(ifo)

        ifos.set_strain_data_from_power_spectral_densities(
            sampling_frequency=self.sampling_frequency,
            duration=self.duration,
            start_time=self.trigger_time - self.duration / 2,
        )

        ifos.inject_signal(
            waveform_generator=waveform_generator, parameters=self.injection_parameters
        )

        self.interferometers = ifos

    @property
    def psd_file_dict(self):
        if self.psd_files is None:
            logger.debug("Unable to construct psd_file_dict")
            return dict()
        psd_file_dict = {}
        for psd_file in self.psd_files:
            ifo_name, file_path = psd_file.split(":")
            psd_file_dict[ifo_name] = file_path
        return psd_file_dict

    def _set_psd_from_file(self, ifo):
        psd_file = self.psd_file_dict[ifo.name]
        logger.info("Setting {} PSD from file {}".format(ifo.name, psd_file))
        ifo.power_spectral_density = PowerSpectralDensity.from_power_spectral_density_file(
            psd_file=psd_file
        )

    def _set_interferometers_from_data(self):
        """ Method to generate the interferometers data from data"""
        end_time = self.start_time + self.duration
        ifo_list = []
        for det in self.detectors:
            logger.info("Getting analysis-segment data for {}".format(det))
            data = self._get_data(det, self.channel_type, self.start_time, end_time)
            ifo = bilby.gw.detector.get_empty_interferometer(det)
            ifo.strain_data.set_from_gwpy_timeseries(data)

            if det in self.psd_file_dict:
                self._set_psd_from_file(ifo)
            else:
                logger.info("Setting PSD for {} from data".format(det))
                # psd_start_time is given relative to the segment start time
                # so here we calculate the actual start time
                actual_psd_start_time = self.start_time + self.psd_start_time
                actual_psd_end_time = actual_psd_start_time + self.psd_duration
                logger.info("Getting psd-segment data for {}".format(det))
                psd_data = self._get_data(
                    det, self.channel_type, actual_psd_start_time, actual_psd_end_time
                )
                roll_off = 0.2
                psd_alpha = 2 * roll_off / self.duration
                overlap = self.psd_fractional_overlap * self.duration
                logger.info(
                    "PSD settings: window=Tukey, Tukey-alpha={} roll-off={},"
                    " overlap={}, method={}".format(
                        psd_alpha, roll_off, overlap, self.psd_method
                    )
                )
                psd = psd_data.psd(
                    fftlength=self.duration,
                    overlap=overlap,
                    window=("tukey", psd_alpha),
                    method=self.psd_method,
                )
                ifo.power_spectral_density = PowerSpectralDensity(
                    frequency_array=psd.frequencies.value, psd_array=psd.value
                )
            ifo_list.append(ifo)
        self.interferometers = bilby.gw.detector.InterferometerList(ifo_list)

    def _get_data(self, det, channel_type, start_time, end_time):
        """ Read in data using gwpy

        This first uses the `gwpy.timeseries.TimeSeries.get()` method to acces
        the data, if this fails, it then attempts to use `fetch_open_data()` as
        a fallback.

        Parameters
        ----------
        channel_type: str, or list of strings
            The full channel name is formed from <det>:<channel_type>, see
            bilby_pipe_generation --help for more information. If given as a
            list each type will be tried and the first success returned.
        start_time, end_time: float
            GPS start and end time of segment
        """
        data = None
        for ct in list(channel_type):
            channel = "{}:{}".format(det, ct)
            try:
                data = self._gwpy_get(det, channel, start_time, end_time)
                break
            except RuntimeError as e:
                logger.info("Unable to read data for channel {}".format(channel))
                logger.debug("Error message {}".format(e))
            except ImportError:
                logger.info("Unable to read data as NDS2 is not installed")
        if data is None:
            logger.warning(
                "Attempts to download data failed, trying with `fetch_open_data`"
            )
            data = gwpy.timeseries.TimeSeries.fetch_open_data(det, start_time, end_time)

        data = data.resample(self.sampling_frequency)
        return data

    def _gwpy_get(self, det, channel, start_time, end_time):
        logger.info(
            "Calling TimeSeries.get({}, start_time={}, end_time={})".format(
                channel, start_time, end_time
            )
        )
        data = gwpy.timeseries.TimeSeries.get(
            channel, start_time, end_time, verbose=True
        )
        return data

    @property
    def interferometers(self):
        """ A bilby.gw.detector.InterferometerList """
        try:
            return self._interferometers
        except AttributeError:
            raise ValueError(
                "interferometers unset, did you provide a set-data method?"
            )

    @interferometers.setter
    def interferometers(self, interferometers):
        self._interferometers = interferometers
        self.data_set = True

    def save_interferometer_list(self):
        """ Method to dump the saved data to disk for later analysis """
        data_dump = DataDump(
            outdir=self.data_directory,
            label=self.label,
            idx=self.idx,
            trigger_time=self.trigger_time,
            interferometers=self.interferometers,
            meta_data=self.meta_data,
        )
        data_dump.to_pickle()


def create_generation_parser():
    return create_parser(
        pipe_args=False,
        job_args=True,
        run_spec=True,
        pe_summary=False,
        injection=True,
        data_gen=True,
        waveform=True,
        generation=True,
        analysis=False,
    )


def main():
    args, unknown_args = parse_args(sys.argv[1:], create_generation_parser())
    data = DataGenerationInput(args, unknown_args)
    data.save_interferometer_list()
    if args.create_plots:
        data.interferometers.plot_data(outdir=data.data_directory, label=data.label)
