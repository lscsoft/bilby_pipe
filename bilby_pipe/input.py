#!/usr/bin/env python
"""
Module containing the main input class
"""
from __future__ import division, print_function

import glob
import json
import os
from importlib import import_module

import numpy as np
import pandas as pd

import bilby

from . import utils
from .utils import (
    BilbyPipeError,
    BilbyPipeInternalError,
    convert_string_to_dict,
    get_geocent_prior,
    logger,
)


class Input(object):
    """ Superclass of input handlers """

    @property
    def complete_ini_file(self):
        return "{}/{}_config_complete.ini".format(self.outdir, self.label)

    @property
    def idx(self):
        """ The level A job index """
        return self._idx

    @idx.setter
    def idx(self, idx):
        self._idx = idx

    @property
    def known_detectors(self):
        try:
            return self._known_detectors
        except AttributeError:
            return ["H1", "L1", "V1"]

    @known_detectors.setter
    def known_detectors(self, known_detectors):
        self._known_detectors = utils.convert_detectors_input(known_detectors)

    @property
    def detectors(self):
        """ A list of the detectors to include, e.g., ['H1', 'L1'] """
        return self._detectors

    @detectors.setter
    def detectors(self, detectors):
        self._detectors = utils.convert_detectors_input(detectors)
        self._check_detectors_against_known_detectors()

    def _check_detectors_against_known_detectors(self):
        for element in self.detectors:
            if element not in self.known_detectors:
                raise BilbyPipeError(
                    'detectors contains "{}" not in the known '
                    "detectors list: {} ".format(element, self.known_detectors)
                )

    @staticmethod
    def _split_string_by_space(string):
        """ Converts "H1 L1" to ["H1", "L1"] """
        return string.split(" ")

    @staticmethod
    def _convert_string_to_list(string):
        """ Converts various strings to a list """
        string = string.replace(",", " ")
        string = string.replace("[", "")
        string = string.replace("]", "")
        string = string.replace('"', "")
        string = string.replace("'", "")
        string_list = string.split()
        return string_list

    @property
    def outdir(self):
        """ The path to the directory where output will be stored """
        utils.check_directory_exists_and_if_not_mkdir(self._outdir)
        return self._outdir

    @outdir.setter
    def outdir(self, outdir):
        self._outdir = os.path.relpath(outdir)

    @property
    def submit_directory(self):
        """ The path to the directory where submit output will be stored """
        path = os.path.join(self._outdir, "submit")
        utils.check_directory_exists_and_if_not_mkdir(path)
        return path

    @property
    def log_directory(self):
        """ The top-level directory for the log directories """
        utils.check_directory_exists_and_if_not_mkdir(self._log_directory)
        return self._log_directory

    @log_directory.setter
    def log_directory(self, log_directory):
        if log_directory is None:
            self._log_directory = self._outdir
        else:
            self._log_directory = log_directory

    @property
    def data_generation_log_directory(self):
        """ The path to the directory where generation logs will be stored """
        path = os.path.join(self.log_directory, "log_data_generation")
        utils.check_directory_exists_and_if_not_mkdir(path)
        return path

    @property
    def data_analysis_log_directory(self):
        """ The path to the directory where analysis logs will be stored """
        path = os.path.join(self.log_directory, "log_data_analysis")
        utils.check_directory_exists_and_if_not_mkdir(path)
        return path

    @property
    def summary_log_directory(self):
        """ The path to the directory where pesummary logs will be stored """
        path = os.path.join(self.log_directory, "log_results_page")
        utils.check_directory_exists_and_if_not_mkdir(path)
        return path

    @property
    def data_directory(self):
        """ The path to the directory where data output will be stored """
        path = os.path.join(self._outdir, "data")
        utils.check_directory_exists_and_if_not_mkdir(path)
        return path

    @property
    def result_directory(self):
        """ The path to the directory where result output will be stored """
        path = os.path.join(self._outdir, "result")
        utils.check_directory_exists_and_if_not_mkdir(path)
        return path

    @property
    def webdir(self):
        utils.check_directory_exists_and_if_not_mkdir(self._webdir)
        return self._webdir

    @webdir.setter
    def webdir(self, webdir):
        if webdir is None:
            self._webdir = os.path.join(self.outdir, "results_page")
        else:
            self._webdir = webdir

    @property
    def gps_file(self):
        """ The gps file containing the list of gps times """
        return self._gps_file

    @gps_file.setter
    def gps_file(self, gps_file):
        """ Set the gps_file

        At setting, will check the file exists, read the contents, identify
        which element to generate data for, and create the interferometers.
        """
        if gps_file is None:
            self._gps_file = None
            return
        elif os.path.isfile(gps_file):
            self._gps_file = os.path.relpath(gps_file)
        else:
            raise FileNotFoundError(
                "Input file gps_file={} not understood".format(gps_file)
            )

        self._parse_gps_file()

    def _parse_gps_file(self):
        gpstimes = self.read_gps_file()
        n = len(gpstimes)
        logger.info("{} start times found in gps_file={}".format(n, self.gps_file))
        self.gpstimes = gpstimes

    def read_gps_file(self):
        gpstimes = np.loadtxt(self.gps_file, ndmin=1)
        return gpstimes

    @property
    def timeslide_file(self):
        """Timeslide file.

        Timeslide file containing the list of timeslides to apply to each
        detector's start time.
        """
        return self._timeslide_file

    @timeslide_file.setter
    def timeslide_file(self, timeslide_file):
        """Set the timeslide_file.

        At setting, will check the file exists, read the contents,
        save the timeslide value for each of the detectors.
        """
        if timeslide_file is None:
            self._timeslide_file = None
            return
        elif os.path.isfile(timeslide_file):
            self._timeslide_file = os.path.relpath(timeslide_file)
        else:
            raise FileNotFoundError(
                "Input file timeslide_file={} not understood".format(timeslide_file)
            )

        if hasattr(self, "_timeslide_file"):
            self._parse_timeslide_file()
        else:
            logger.debug("No _parse_timeslide_file method present")

    def read_timeslide_file(self):
        """Read timeslide file.

        Each row of file is an array, hence ndmin = 2
        [ [timshift1,...], [], [] ...]
        """
        timeslides_list = np.loadtxt(self.timeslide_file, ndmin=2)
        return timeslides_list

    def _parse_timeslide_file(self):
        """Parse the timeslide file and check for correctness.

        Sets the attribute "timeslides" if timeslide file correctly formatted
        and passed to Inputs()
        """
        timeslides_list = self.read_timeslide_file()

        number_rows, number_columns = timeslides_list.shape
        if number_columns != len(self.detectors):
            raise BilbyPipeError(
                "The timeslide file must have one column for each of the detectors. "
                "Number Cols: {}, Number Detectors: {}".format(
                    number_columns, len(self.detectors)
                )
            )
        if number_rows != len(self.gpstimes):
            raise BilbyPipeError(
                "The timeslide file must have one row for each gps time. "
                "Number Rows: {}, Number Gps Times: {}".format(
                    number_rows, len(self.gpstimes)
                )
            )
        times = np.hsplit(timeslides_list, len(self.detectors))
        self.timeslides = {}
        for i in range(len(self.detectors)):
            self.timeslides.update({self.detectors[i]: times[i].flatten()})
        logger.info(
            "{} timeslides found in timeslide_file={}".format(
                number_rows, self.timeslide_file
            )
        )

    def get_timeslide_dict(self, idx):
        """Return a specific timeslide value from the timeslide file.

        Given an index, the dict of {detector: timeslide value} is created for
        the specific index and returned.
        """
        if not hasattr(self, "timeslides"):
            raise BilbyPipeError("Timeslide file must be provided.")
        if any(len(t) <= idx for t in self.timeslides.values()):
            raise BilbyPipeError(
                "Timeslide index={} > number of timeslides available.".format(idx)
            )
        timeslide_val = {
            det: timeslide[idx] for det, timeslide in self.timeslides.items()
        }
        logger.info("Timeslide value: {}".format(timeslide_val))
        return timeslide_val

    @property
    def bilby_frequency_domain_source_model(self):
        """
        The bilby function to pass to the waveform_generator

        This can be a function defined in an external package.
        """
        if self.frequency_domain_source_model in bilby.gw.source.__dict__.keys():
            model = self._frequency_domain_source_model
            logger.info("Using the {} source model".format(model))
            return bilby.gw.source.__dict__[model]
        elif "." in self.frequency_domain_source_model:
            split_model = self._frequency_domain_source_model.split(".")
            module = ".".join(split_model[:-1])
            func = split_model[-1]
            return getattr(import_module(module), func)
        else:
            raise BilbyPipeError(
                "No source model {} found.".format(self._frequency_domain_source_model)
            )

    @property
    def reference_frequency(self):
        return self._reference_frequency

    @reference_frequency.setter
    def reference_frequency(self, reference_frequency):
        self._reference_frequency = float(reference_frequency)

    def get_default_waveform_arguments(self):
        return dict(
            reference_frequency=self.reference_frequency,
            waveform_approximant=self.waveform_approximant,
            minimum_frequency=self.minimum_frequency,
            catch_waveform_errors=self.catch_waveform_errors,
            pn_spin_order=self.pn_spin_order,
            pn_tidal_order=self.pn_tidal_order,
            pn_phase_order=self.pn_phase_order,
            pn_amplitude_order=self.pn_amplitude_order,
        )

    def get_injection_waveform_arguments(self):
        """Get the dict of the waveform arguments needed for creating injections.

        Defaults the injection-waveform-approximant to waveform-approximant, if
        no injection-waveform-approximant provided. Note that the default
        waveform-approximant is `IMRPhenomPv2`.
        """
        if self.injection_waveform_approximant is None:
            self.injection_waveform_approximant = self.waveform_approximant
        return dict(
            reference_frequency=self.reference_frequency,
            waveform_approximant=self.injection_waveform_approximant,
            minimum_frequency=self.minimum_frequency,
            pn_spin_order=self.pn_spin_order,
            pn_tidal_order=self.pn_tidal_order,
            pn_phase_order=self.pn_phase_order,
            pn_amplitude_order=self.pn_amplitude_order,
        )

    @property
    def bilby_roq_frequency_domain_source_model(self):
        if "binary_neutron_star" in self.frequency_domain_source_model:
            logger.info("Using the binary_neutron_star_roq source model")
            return bilby.gw.source.binary_neutron_star_roq
        elif "binary_black_hole" in self.frequency_domain_source_model:
            logger.info("Using the binary_black_hole_roq source model")
            return bilby.gw.source.binary_black_hole_roq
        else:
            raise BilbyPipeError("Unable to determine roq_source from source model")

    @property
    def frequency_domain_source_model(self):
        """ String of which frequency domain source model to use """
        return self._frequency_domain_source_model

    @frequency_domain_source_model.setter
    def frequency_domain_source_model(self, frequency_domain_source_model):
        self._frequency_domain_source_model = frequency_domain_source_model

    @property
    def trigger_time(self):
        return self._trigger_time

    @trigger_time.setter
    def trigger_time(self, trigger_time):
        self._trigger_time = trigger_time
        if trigger_time is not None:
            logger.info("Setting trigger time {}".format(trigger_time))

    @property
    def start_time(self):
        if hasattr(self, "_start_time"):
            self._verify_start_time(self._start_time)
            return self._start_time
        try:
            self._start_time = (
                self.trigger_time + self.post_trigger_duration - self.duration
            )
            return self._start_time
        except AttributeError:
            logger.warning("Unable to calculate default segment start time")
            return None

    def _verify_start_time(self, start_time):
        try:
            inferred_start_time = (
                self.trigger_time + self.post_trigger_duration - self.duration
            )
        except AttributeError:
            logger.warning("Unable to verify start-time consistency")
            return

        if inferred_start_time != start_time:
            raise BilbyPipeError("Unexpected behaviour encountered with start time")

    @start_time.setter
    def start_time(self, start_time):
        self._verify_start_time(start_time)
        self._start_time = start_time
        if start_time is not None:
            logger.info("Setting segment start time {}".format(start_time))

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, duration):
        self._duration = duration
        if duration is not None:
            logger.info("Setting segment duration {}s".format(duration))

    @property
    def injection_numbers(self):
        if hasattr(self, "_injection_numbers"):
            return self._injection_numbers
        else:
            raise BilbyPipeInternalError("Injection numbers requested, but not yet set")

    @injection_numbers.setter
    def injection_numbers(self, injection_numbers):
        if (
            injection_numbers is None
            or len(injection_numbers) == 0
            or injection_numbers[0] is None
            or injection_numbers[0] == "None"
        ):
            self._injection_numbers = None
            return
        if all([isinstance(val, int) for val in injection_numbers]):
            self._injection_numbers = injection_numbers
        else:
            raise BilbyPipeError(
                "Invalid injection numbers {}".format(injection_numbers)
            )

    @property
    def injection_df(self):
        return self._injection_df

    @injection_df.setter
    def injection_df(self, injection_df):
        if isinstance(injection_df, pd.DataFrame) is False:
            raise BilbyPipeError("Setting injection df with non-pandas DataFrame")
        elif self.injection_numbers is not None:
            logger.info(
                "Truncating injection injection df to rows {}".format(
                    self.injection_numbers
                )
            )
            try:
                self._injection_df = injection_df.iloc[self.injection_numbers]
            except IndexError:
                raise BilbyPipeError(
                    "Your injection_numbers are incompatible with the injection set"
                )
        else:
            self._injection_df = injection_df

    @property
    def injection_file(self):
        return self._injection_file

    @injection_file.setter
    def injection_file(self, injection_file):
        if injection_file is None:
            logger.debug("No injection file set")
            self._injection_file = None
        elif os.path.isfile(injection_file):
            self._injection_file = os.path.relpath(injection_file)
            self.injection_df = self.read_injection_file(injection_file)
            self.total_number_of_injections = len(self.injection_df)
            self.injection = True
        else:
            raise FileNotFoundError(
                "Injection file {} not found".format(injection_file)
            )

    @property
    def injection_dict(self):
        return self._injection_dict

    @injection_dict.setter
    def injection_dict(self, injection_dict):
        if injection_dict is None:
            self._injection_dict = None
            return
        elif isinstance(injection_dict, str):
            self._injection_dict = convert_string_to_dict(injection_dict)
        elif isinstance(injection_dict, dict):
            self._injection_dict = injection_dict
        else:
            raise BilbyPipeError("injection-dict can not be coerced to a dict")

        self.injection_df = pd.DataFrame(self._injection_dict, index=[0])
        self.total_number_of_injections = 1
        self.injection = True

    @staticmethod
    def read_injection_file(injection_file):
        if "json" in injection_file:
            return Input.read_json_injection_file(injection_file)
        elif "dat" in injection_file:
            return Input.read_dat_injection_file(injection_file)

    @staticmethod
    def read_json_injection_file(injection_file):
        with open(injection_file, "r") as file:
            injection_dict = json.load(
                file, object_hook=bilby.core.result.decode_bilby_json
            )
        injection_df = injection_dict["injections"]
        try:
            injection_df = pd.DataFrame(injection_df)
        except ValueError:
            # If injection_df is a dictionary of single elements, set the index-array in pandas
            injection_df = pd.DataFrame(injection_df, index=[0])
        return injection_df

    @staticmethod
    def read_dat_injection_file(injection_file):
        return pd.read_csv(injection_file, delim_whitespace=True)

    @property
    def spline_calibration_envelope_dict(self):
        return self._spline_calibration_envelope_dict

    @spline_calibration_envelope_dict.setter
    def spline_calibration_envelope_dict(self, spline_calibration_envelope_dict):
        if spline_calibration_envelope_dict is not None:
            self._spline_calibration_envelope_dict = convert_string_to_dict(
                spline_calibration_envelope_dict, "spline-calibration-envelope-dict"
            )
        else:
            logger.debug("spline_calibration_envelope_dict")
            self._spline_calibration_envelope_dict = None

    @property
    def spline_calibration_amplitude_uncertainty_dict(self):
        return self._spline_calibration_amplitude_uncertainty_dict

    @spline_calibration_amplitude_uncertainty_dict.setter
    def spline_calibration_amplitude_uncertainty_dict(
        self, spline_calibration_amplitude_uncertainty_dict
    ):
        if spline_calibration_amplitude_uncertainty_dict is not None:
            self._spline_calibration_amplitude_uncertainty_dict = convert_string_to_dict(
                spline_calibration_amplitude_uncertainty_dict,
                "spline-calibration-amplitude-uncertainty-dict",
            )
        else:
            logger.debug("spline_calibration_amplitude_uncertainty_dict")
            self._spline_calibration_amplitude_uncertainty_dict = None

    @property
    def spline_calibration_phase_uncertainty_dict(self):
        return self._spline_calibration_phase_uncertainty_dict

    @spline_calibration_phase_uncertainty_dict.setter
    def spline_calibration_phase_uncertainty_dict(
        self, spline_calibration_phase_uncertainty_dict
    ):
        if spline_calibration_phase_uncertainty_dict is not None:
            self._spline_calibration_phase_uncertainty_dict = convert_string_to_dict(
                spline_calibration_phase_uncertainty_dict,
                "spline-calibration-phase-uncertainty-dict",
            )
        else:
            logger.debug("spline_calibration_phase_uncertainty_dict")
            self._spline_calibration_phase_uncertainty_dict = None

    @property
    def minimum_frequency(self):
        """ The minimum frequency

        If a per-detector dictionary is given, this will return the minimum
        frequency value. To access the dictionary,
        see self.minimum_frequency_dict
        """
        return self._minimum_frequency

    @minimum_frequency.setter
    def minimum_frequency(self, minimum_frequency):
        if minimum_frequency is None:
            self._minimum_frequency = None
            self.minimum_frequency_dict = {det: None for det in self.detectors}
        else:
            try:
                self._minimum_frequency = float(minimum_frequency)
                self.minimum_frequency_dict = {
                    det: float(minimum_frequency) for det in self.detectors
                }
            except ValueError:
                self.minimum_frequency_dict = convert_string_to_dict(
                    minimum_frequency, "minimum-frequency"
                )
                self._minimum_frequency = np.min(
                    [xx for xx in self._minimum_frequency_dict.values()]
                ).item()

    @property
    def minimum_frequency_dict(self):
        return self._minimum_frequency_dict

    @minimum_frequency_dict.setter
    def minimum_frequency_dict(self, minimum_frequency_dict):
        for det in self.detectors:
            if det not in minimum_frequency_dict.keys():
                raise BilbyPipeError(
                    "Input minimum frequency required for detector {}".format(det)
                )
        self._minimum_frequency_dict = minimum_frequency_dict

    @property
    def maximum_frequency(self):
        """ The maximum frequency

        If a per-detector dictionary is given, this will return the maximum
        frequency value. To access the dictionary,
        see self.maximum_frequency_dict
        """

        return self._maximum_frequency

    @maximum_frequency.setter
    def maximum_frequency(self, maximum_frequency):
        if maximum_frequency is None:
            self._maximum_frequency = None
            self.maximum_frequency_dict = {det: None for det in self.detectors}
        else:
            try:
                self._maximum_frequency = float(maximum_frequency)
                self.maximum_frequency_dict = {
                    det: float(maximum_frequency) for det in self.detectors
                }
            except ValueError:
                self.maximum_frequency_dict = convert_string_to_dict(
                    maximum_frequency, "maximum-frequency"
                )
                self._maximum_frequency = np.max(
                    [xx for xx in self._maximum_frequency_dict.values()]
                ).item()

    @property
    def maximum_frequency_dict(self):
        return self._maximum_frequency_dict

    @maximum_frequency_dict.setter
    def maximum_frequency_dict(self, maximum_frequency_dict):
        for det in maximum_frequency_dict.keys():
            if det not in self.detectors:
                raise BilbyPipeError(
                    "Input maximum frequency required for detector {}".format(det)
                )
        self._maximum_frequency_dict = maximum_frequency_dict

    @property
    def default_prior_files(self):
        return self.get_default_prior_files()

    @staticmethod
    def get_default_prior_files():
        """ Returns a dictionary of the default priors """
        prior_files_glob = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "data_files/*prior"
        )
        filenames = glob.glob(prior_files_glob)
        return {os.path.basename(ff).rstrip(".prior"): ff for ff in filenames}

    def get_distance_file_lookup_table(self, prior_file_str):
        direc = os.path.dirname(self.default_prior_files[prior_file_str])
        fname = "{}_distance_marginalization_lookup.npz".format(prior_file_str)
        return os.path.join(direc, fname)

    @property
    def prior_file(self):
        return self._prior_file

    @prior_file.setter
    def prior_file(self, prior_file):
        if prior_file is None:
            self._prior_file = None
        elif os.path.isfile(prior_file):
            self._prior_file = prior_file
        elif os.path.isfile(os.path.basename(prior_file)):
            # Allows for the prior-file to be moved to the local directory (file-transfer mechanism)
            self._prior_file = os.path.basename(prior_file)
        elif prior_file in self.default_prior_files:
            self._prior_file = self.default_prior_files[prior_file]
            self.distance_marginalization_lookup_table = self.get_distance_file_lookup_table(
                prior_file
            )
        else:
            raise FileNotFoundError("No prior file {} available".format(prior_file))

        logger.info("Setting prior-file to {}".format(self._prior_file))

    @property
    def prior_dict(self):
        """ The input prior_dict from the ini (if given)

        Note, this is not the bilby prior (see self.priors for that), this is
        a key-val dictionary where the val's are strings which are converting
        into bilby priors in `_get_prior
        """
        return self._prior_dict

    @prior_dict.setter
    def prior_dict(self, prior_dict):
        if isinstance(prior_dict, dict):
            prior_dict = prior_dict
        elif isinstance(prior_dict, str):
            prior_dict = utils.convert_prior_string_input(prior_dict)
        elif prior_dict is None:
            self._prior_dict = None
            return
        else:
            raise BilbyPipeError("prior_dict={} not understood".format(prior_dict))

        self._prior_dict = {
            self._convert_prior_dict_key(key): val for key, val in prior_dict.items()
        }

    @staticmethod
    def _convert_prior_dict_key(key):
        """ Converts the prior dict key to standard form

        In the ini read, mass_1 -> mass-1, this corrects for that
        """
        if "-" in key:
            key_replaced = key.replace("-", "_")
            logger.debug("Converting prior-dict key {} to {}".format(key, key_replaced))
            key = key_replaced
        return key

    @property
    def distance_marginalization_lookup_table(self):
        return self._distance_marginalization_lookup_table

    @distance_marginalization_lookup_table.setter
    def distance_marginalization_lookup_table(
        self, distance_marginalization_lookup_table
    ):
        if distance_marginalization_lookup_table is None:
            if hasattr(self, "_distance_marginalization_lookup_table"):
                pass
            else:
                self._distance_marginalization_lookup_table = None
        else:
            if hasattr(self, "_distance_marginalization_lookup_table"):
                logger.info("Overwriting distance_marginalization_lookup_table")
            self._distance_marginalization_lookup_table = (
                distance_marginalization_lookup_table
            )

    @property
    def default_prior(self):
        return getattr(self, "_default_prior", None)

    @default_prior.setter
    def default_prior(self, default_prior):
        self._default_prior = default_prior

    @property
    def combined_default_prior_dicts(self):
        d = bilby.core.prior.__dict__.copy()
        d.update(bilby.gw.prior.__dict__)
        return d

    def create_geocent_time_prior(self):
        cond_a = getattr(self, "trigger_time", None) is not None
        cond_b = getattr(self, "deltaT", None) is not None
        if cond_a and cond_b:
            logger.info(
                "Setting geocent time prior using trigger-time={} and deltaT={}".format(
                    self.trigger_time, self.deltaT
                )
            )
            geocent_time_prior = get_geocent_prior(
                geocent_time=self.trigger_time, uncertainty=self.deltaT / 2.0
            )
        else:
            raise BilbyPipeError("Unable to set geocent_time prior from trigger_time")

        return geocent_time_prior

    @property
    def priors(self):
        """ Read in and compose the prior at run-time """
        if getattr(self, "_priors", None) is None:
            self._priors = self._get_priors()
        return self._priors

    @priors.setter
    def priors(self, priors):
        self._priors = priors

    def _get_priors(self, add_geocent_time=True):
        """ Construct the priors

        Parameters
        ----------
        add_geocent_time: bool
            If True, the geocent time prior is constructed from either the
            prior file or the trigger time. If False (used for the overview
            page where a single time-prior doesn't make sense), this isn't
            added to the prior

        Returns
        -------
        prior: bilby.core.prior.PriorDict
            The generated prior
        """
        if self.default_prior in self.combined_default_prior_dicts.keys():
            prior_class = self.combined_default_prior_dicts[self.default_prior]
            if self.prior_dict is not None:
                priors = prior_class(dictionary=self.prior_dict)
            else:
                priors = prior_class(filename=self.prior_file)
        else:
            raise ValueError("Unable to set prior: default_prior unavailable")

        if priors.get("geocent_time", None) is None and add_geocent_time:
            priors["geocent_time"] = self.create_geocent_time_prior()
        else:
            logger.info("Using geocent_time prior from prior_file")

        if self.calibration_model is not None:
            priors.update(self.calibration_prior)
        return priors

    @property
    def calibration_model(self):
        return getattr(self, "_calibration_model", None)

    @calibration_model.setter
    def calibration_model(self, calibration_model):
        if calibration_model is not None:
            logger.info("Setting calibration_model={}".format(calibration_model))
            self._calibration_model = calibration_model
        else:
            logger.info(
                "No calibration_model model provided, calibration "
                "marginalization will not be used"
            )
            self._calibration_model = None

    @property
    def calibration_prior(self):
        if self.calibration_model is None:
            return None
        if getattr(self, "_calibration_prior", None) is not None:
            return self._calibration_prior
        self._calibration_prior = bilby.core.prior.PriorDict()
        if self.calibration_model is not None:
            for det in self.detectors:
                if det in self.spline_calibration_envelope_dict:
                    logger.info(
                        "Creating calibration prior for {} from {}".format(
                            det, self.spline_calibration_envelope_dict[det]
                        )
                    )
                    self._calibration_prior.update(
                        bilby.gw.prior.CalibrationPriorDict.from_envelope_file(
                            self.spline_calibration_envelope_dict[det],
                            minimum_frequency=self.minimum_frequency_dict[det],
                            maximum_frequency=self.maximum_frequency_dict[det],
                            n_nodes=self.spline_calibration_nodes,
                            label=det,
                        )
                    )
                elif (
                    det in self.spline_calibration_amplitude_uncertainty_dict
                    and det in self.spline_calibration_phase_uncertainty_dict
                ):
                    logger.info(
                        "Creating calibration prior for {} from "
                        "provided constant uncertainty values.".format(det)
                    )
                    self._calibration_prior.update(
                        bilby.gw.prior.CalibrationPriorDict.constant_uncertainty_spline(
                            amplitude_sigma=self.spline_calibration_amplitude_uncertainty_dict[
                                det
                            ],
                            phase_sigma=self.spline_calibration_phase_uncertainty_dict[
                                det
                            ],
                            minimum_frequency=self.minimum_frequency_dict[det],
                            maximum_frequency=self.maximum_frequency_dict[det],
                            n_nodes=self.spline_calibration_nodes,
                            label=det,
                        )
                    )
                else:
                    logger.warning(f"No calibration information for {det}")
        return self._calibration_prior

    @property
    def calibration_model(self):
        return getattr(self, "_calibration_model", None)

    @calibration_model.setter
    def calibration_model(self, calibration_model):
        if calibration_model is not None:
            logger.info("Setting calibration_model={}".format(calibration_model))
            self._calibration_model = calibration_model
        else:
            logger.info(
                "No calibration_model model provided, calibration "
                "marginalization will not be used"
            )
            self._calibration_model = None

    @property
    def likelihood(self):

        self.search_priors = self.priors.copy()
        likelihood_kwargs = dict(
            interferometers=self.interferometers,
            waveform_generator=self.waveform_generator,
            priors=self.search_priors,
            phase_marginalization=self.phase_marginalization,
            distance_marginalization=self.distance_marginalization,
            distance_marginalization_lookup_table=self.distance_marginalization_lookup_table,
            time_marginalization=self.time_marginalization,
        )

        if getattr(self, "likelihood_lookup_table", None) is not None:
            logger.info("Using internally loaded likelihood_lookup_table")
            likelihood_kwargs["distance_marginalization_lookup_table"] = getattr(
                self, "likelihood_lookup_table"
            )

        if self.likelihood_type == "GravitationalWaveTransient":
            Likelihood = bilby.gw.likelihood.GravitationalWaveTransient
            likelihood_kwargs.update(jitter_time=self.jitter_time)

        elif self.likelihood_type == "ROQGravitationalWaveTransient":
            Likelihood = bilby.gw.likelihood.ROQGravitationalWaveTransient

            if self.time_marginalization:
                logger.warning(
                    "Time marginalization not implemented for "
                    "ROQGravitationalWaveTransient: option ignored"
                )

            likelihood_kwargs.pop("time_marginalization", None)
            likelihood_kwargs.pop("jitter_time", None)
            likelihood_kwargs.update(self.roq_likelihood_kwargs)
        elif "." in self.likelihood_type:
            split_path = self.likelihood_type.split(".")
            module = ".".join(split_path[:-1])
            likelihood_class = split_path[-1]
            Likelihood = getattr(import_module(module), likelihood_class)
            likelihood_kwargs.update(self.extra_likelihood_kwargs)
            if "roq" in self.likelihood_type.lower():
                likelihood_kwargs.pop("time_marginalization", None)
                likelihood_kwargs.pop("jitter_time", None)
                likelihood_kwargs.update(self.roq_likelihood_kwargs)
        else:
            raise ValueError("Unknown Likelihood class {}")

        logger.debug(
            "Initialise likelihood {} with kwargs: \n{}".format(
                Likelihood, likelihood_kwargs
            )
        )

        return Likelihood(**likelihood_kwargs)

    @property
    def extra_likelihood_kwargs(self):
        return self._extra_likelihood_kwargs

    @extra_likelihood_kwargs.setter
    def extra_likelihood_kwargs(self, likelihood_kwargs):
        if isinstance(likelihood_kwargs, str):
            likelihood_kwargs = utils.convert_string_to_dict(likelihood_kwargs)
        elif likelihood_kwargs is None:
            likelihood_kwargs = dict()
        elif not isinstance(likelihood_kwargs, dict):
            raise TypeError(
                "Type {} not understood for likelihood kwargs.".format(
                    type(likelihood_kwargs)
                )
            )
        forbidden_keys = [
            "interferometers",
            "waveform_generator",
            "priors",
            "distance_marginalization",
            "time_marginalization",
            "phase_marginalization",
            "jitter_time",
            "distance_marginalization_lookup_table",
        ]
        if "roq" in self.likelihood_type.lower():
            forbidden_keys += ["weights", "roq_params", "roq_scale_factor"]
        for key in forbidden_keys:
            if key in likelihood_kwargs:
                raise KeyError(
                    "{} should be passed through named argument not likelihood_kwargs".format(
                        key
                    )
                )
        self._extra_likelihood_kwargs = likelihood_kwargs

    @property
    def roq_likelihood_kwargs(self):
        if hasattr(self, "likelihood_roq_params"):
            params = self.likelihood_roq_params
        else:
            params = np.genfromtxt(self.roq_folder + "/params.dat", names=True)

        if hasattr(self, "likelihood_roq_weights"):
            weights = self.likelihood_roq_weights
        else:
            weights = self.meta_data["weight_file"]
            logger.info("Loading ROQ weights from {}".format(weights))

        return dict(
            weights=weights, roq_params=params, roq_scale_factor=self.roq_scale_factor
        )

    @property
    def parameter_conversion(self):
        if "binary_neutron_star" in self._frequency_domain_source_model:
            return bilby.gw.conversion.convert_to_lal_binary_neutron_star_parameters
        elif "binary_black_hole" in self._frequency_domain_source_model:
            return bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters
        else:
            return None

    @property
    def waveform_generator(self):
        waveform_arguments = self.get_default_waveform_arguments()

        if "ROQ" in self.likelihood_type:
            logger.info(
                "Using {} likelihood with roq-folder={}".format(
                    self.likelihood_type, self.roq_folder
                )
            )
            freq_nodes_linear = np.load(self.roq_folder + "/fnodes_linear.npy")
            freq_nodes_quadratic = np.load(self.roq_folder + "/fnodes_quadratic.npy")
            freq_nodes_linear *= self.roq_scale_factor
            freq_nodes_quadratic *= self.roq_scale_factor

            waveform_arguments["frequency_nodes_linear"] = freq_nodes_linear
            waveform_arguments["frequency_nodes_quadratic"] = freq_nodes_quadratic

            waveform_generator = self.waveform_generator_class(
                frequency_domain_source_model=self.bilby_roq_frequency_domain_source_model,
                sampling_frequency=self.interferometers.sampling_frequency,
                duration=self.interferometers.duration,
                start_time=self.interferometers.start_time,
                parameter_conversion=self.parameter_conversion,
                waveform_arguments=waveform_arguments,
            )

        else:
            waveform_generator = self.waveform_generator_class(
                frequency_domain_source_model=self.bilby_frequency_domain_source_model,
                sampling_frequency=self.interferometers.sampling_frequency,
                duration=self.interferometers.duration,
                parameter_conversion=self.parameter_conversion,
                start_time=self.interferometers.start_time,
                waveform_arguments=waveform_arguments,
            )

        return waveform_generator

    @property
    def waveform_generator_class(self):
        return self._waveform_generator_class

    @waveform_generator_class.setter
    def waveform_generator_class(self, class_name):
        if "." in class_name:
            module = ".".join(class_name.split(".")[:-1])
            class_name = class_name.split(".")[-1]
        else:
            module = "bilby.gw.waveform_generator"
        wfg_class = getattr(import_module(module), class_name, None)
        if wfg_class is not None:
            self._waveform_generator_class = wfg_class
        else:
            raise BilbyPipeError(
                "Cannot import waveform generator class {}.{}".format(
                    module, class_name
                )
            )

    @property
    def parameter_generation(self):
        if "binary_neutron_star" in self._frequency_domain_source_model:
            return bilby.gw.conversion.generate_all_bns_parameters
        elif "binary_black_hole" in self._frequency_domain_source_model:
            return bilby.gw.conversion.generate_all_bbh_parameters
        else:
            return None

    @property
    def summarypages_arguments(self):
        return self._summarypages_arguments

    @summarypages_arguments.setter
    def summarypages_arguments(self, summarypages_arguments):
        if summarypages_arguments is None:
            self._summarypages_arguments = None
            return
        string = summarypages_arguments
        if "{" in string and "}" in string:
            self._summarypages_arguments = convert_string_to_dict(string)
        else:
            self._summarypages_arguments = summarypages_arguments

    @property
    def postprocessing_arguments(self):
        return self._postprocessing_arguments

    @postprocessing_arguments.setter
    def postprocessing_arguments(self, postprocessing_arguments):
        if postprocessing_arguments in [None, "None"]:
            self._postprocessing_arguments = None
        elif postprocessing_arguments == [None]:
            self._postprocessing_arguments = None
        elif isinstance(postprocessing_arguments, str):
            self._postprocessing_arguments = postprocessing_arguments.split(" ")
        else:
            self._postprocessing_arguments = postprocessing_arguments
