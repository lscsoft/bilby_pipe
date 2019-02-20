#!/usr/bin/env python
"""
Module containing the tools for data generation
"""
from __future__ import division, print_function

import sys
import os
import urllib
import urllib.request

import bilby
import deepdish

from bilby_pipe.utils import logger, BilbyPipeError
from bilby_pipe.main import DataDump, parse_args
from bilby_pipe.input import Input
from bilby_pipe.parser import create_parser


class DataGenerationInput(Input):
    """ Handles user-input and creation of intermediate ifo list

    Parameters
    ----------
    parser: configargparse.ArgParser, optional
        The parser containing the command line / ini file inputs
    args_list: list, optional
        A list of the arguments to parse. Defauts to `sys.argv[1:]`

    """

    def __init__(self, args, unknown_args):

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
        self.calibration = args.calibration
        self.channel_names = args.channel_names
        self.query_types = args.query_types
        self.duration = args.duration
        self.trigger_time = args.trigger_time
        self.post_trigger_duration = args.post_trigger_duration
        self.sampling_frequency = args.sampling_frequency
        self.psd_duration = args.psd_duration
        self.psd_start_time = args.psd_start_time
        self.psd_files = args.psd_files
        self.minimum_frequency = args.minimum_frequency
        self.outdir = args.outdir
        self.label = args.label
        self.frequency_domain_source_model = args.frequency_domain_source_model

        self.gracedb = args.gracedb
        self.gps_file = args.gps_file

        self.waveform_approximant = args.waveform_approximant
        self.reference_frequency = args.reference_frequency
        self.injection_file = args.injection_file

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
    def psd_duration(self):
        return self._psd_duration

    @psd_duration.setter
    def psd_duration(self, psd_duration):
        if psd_duration is None:
            self._psd_duration = 33 * self.duration
        else:
            self._psd_duration = psd_duration
        logger.debug("PSD duration set to {}".format(self.psd_duration))

    @property
    def psd_start_time(self):
        return self._psd_start_time

    @psd_start_time.setter
    def psd_start_time(self, psd_start_time):
        if psd_start_time is None:
            self._psd_start_time = self.trigger_time - self.psd_duration / 2.0
        else:
            self._psd_start_time = psd_start_time
        logger.debug("PSD duration set to {}".format(self.psd_duration))

    @property
    def minimum_frequency(self):
        return self._minimum_frequency

    @minimum_frequency.setter
    def minimum_frequency(self, minimum_frequency):
        self._minimum_frequency = float(minimum_frequency)

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
    def gracedb(self):
        """ The gracedb of the candidate """
        return self._gracedb

    @gracedb.setter
    def gracedb(self, gracedb):
        """ Set the gracedb ID

        At setting, will load the json candidate data and path to the frame
        cache file.
        """
        if gracedb is None:
            self._gracedb = None
        else:
            logger.info("Setting gracedb id to {}".format(gracedb))
            try:
                urllib.request.urlopen("https://google.com", timeout=0.1)
            except urllib.error.URLError:
                raise BilbyPipeError(
                    "Unable to grab graceDB entry because the network is "
                    "unreachable. Please specify the local-generation argument "
                    "either in the configuration file or by passing the"
                    "--local-generation command line argument"
                )
            candidate, frame_caches = bilby.gw.utils.get_gracedb(
                gracedb,
                self.data_directory,
                self.duration,
                self.calibration,
                self.detectors,
                self.query_types,
            )
            self.meta_data["gracedb_candidate"] = candidate
            self._gracedb = gracedb
            self.trigger_time = candidate["gpstime"]
            self.start_time = (
                self.trigger_time + self.post_trigger_duration - self.duration
            )
            self.frame_caches = frame_caches

    def _parse_gps_file(self):
        gps_start_times = self.read_gps_file()
        self.start_time = gps_start_times[self.idx]
        self.trigger_time = self.start_time + self.duration / 2.0
        self.frame_caches = self.generate_frame_cache_list_from_gpstime()

    def generate_frame_cache_list_from_gpstime(self):
        cache_files = []
        for det in self.detectors:
            cache_files.append(
                bilby.gw.utils.gw_data_find(
                    det,
                    gps_start_time=self.start_time,
                    duration=self.duration,
                    calibration=self.calibration,
                    outdir=self.data_directory,
                )
            )
        return cache_files

    @property
    def frame_caches(self):
        """ A list of paths to the frame-cache files """
        try:
            return self._frame_caches
        except AttributeError:
            raise ValueError("frame_caches list is unset")

    @frame_caches.setter
    def frame_caches(self, frame_caches):
        """ Set the frame_caches, if successfull generate the interferometer list """
        if isinstance(frame_caches, list):
            self._frame_caches = frame_caches
            self._set_interferometers_from_frame_caches(frame_caches)
        elif frame_caches is None:
            self._frame_caches = None
        else:
            raise ValueError("frame_caches list must be a list")

    def _set_interferometers_from_frame_caches(self, frame_caches):
        """ Helper method to set the interferometers from a list of frame_caches

        If no channel names are supplied, an attempt is made by bilby to
        infer the correct channel name.

        Parameters
        ----------
        frame_caches: list
            A list of strings pointing to the frame cache file
        """
        interferometers = bilby.gw.detector.InterferometerList([])
        if self.channel_names is None:
            self.channel_names = [None] * len(frame_caches)
        for cache_file, channel_name in zip(frame_caches, self.channel_names):
            interferometer = bilby.gw.detector.load_data_from_cache_file(
                cache_file=cache_file,
                start_time=self.start_time,
                segment_duration=self.duration,
                psd_duration=self.psd_duration,
                psd_start_time=self.psd_start_time,
                channel_name=None,
                sampling_frequency=self.sampling_frequency,
                roll_off=0.2,
                overlap=0,
                outdir=None,
            )

            interferometer.minimum_frequency = self.minimum_frequency
            interferometers.append(interferometer)
        self.interferometers = interferometers

    @property
    def parameter_conversion(self):
        if "binary_neutron_star" in self.frequency_domain_source_model:
            return bilby.gw.conversion.convert_to_lal_binary_neutron_star_parameters
        elif "binary_black_hole" in self.frequency_domain_source_model:
            return bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters
        else:
            return None

    @property
    def injection_file(self):
        return self._injection_file

    @injection_file.setter
    def injection_file(self, injection_file):
        if injection_file is None:
            logger.debug("No injection file set")
            self._injection_file = None
        elif os.path.isfile(injection_file):
            self._injection_file = os.path.abspath(injection_file)
            injection_dict = deepdish.io.load(injection_file)
            injection_df = injection_dict["injections"]
            self.injection_parameters = injection_df.iloc[self.idx].to_dict()
            self.meta_data["injection_parameters"] = self.injection_parameters
            if self.trigger_time is None:
                self.trigger_time = self.injection_parameters["geocent_time"]
            self._set_interferometers_from_simulation()
        else:
            raise FileNotFoundError(
                "Injection file {} not found".format(injection_file)
            )

    def _set_psds_from_files(self, ifos):
        psd_file_dict = {}
        for psd_file in self.psd_files:
            ifo_name, file_path = psd_file.split(":")
            psd_file_dict[ifo_name] = file_path
        for ifo in [ifo for ifo in ifos if ifo.name in psd_file_dict.keys()]:
            ifo.power_spectral_density = bilby.gw.detector.PowerSpectralDensity.from_power_spectral_density_file(
                psd_file=psd_file_dict[ifo.name]
            )

    def _set_interferometers_from_simulation(self):
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
            self._set_psds_from_files(ifos)

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

    def save_interferometer_list(self):
        data_dump = DataDump(
            outdir=self.data_directory,
            label=self.label,
            idx=self.idx,
            trigger_time=self.trigger_time,
            interferometers=self.interferometers,
            meta_data=self.meta_data,
        )
        data_dump.to_hdf5()

        self.interferometers.plot_data(outdir=self.data_directory, label=self.label)


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
