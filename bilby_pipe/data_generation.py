#!/usr/bin/env python
"""
Module containing the tools for data generation
"""
from __future__ import division, print_function

import os
import sys

import gwpy
import numpy as np

import bilby
from bilby.gw.detector import PowerSpectralDensity
from bilby_pipe.input import Input
from bilby_pipe.main import parse_args
from bilby_pipe.parser import create_parser
from bilby_pipe.plotting_utils import strain_spectogram_plot
from bilby_pipe.utils import (
    BilbyPipeError,
    DataDump,
    convert_string_to_dict,
    get_geocent_time_with_uncertainty,
    get_version_information,
    is_a_power_of_2,
    log_version_information,
    logger,
)

# fmt: off
import matplotlib  # isort:skip
matplotlib.use("agg")
# fmt: on


try:
    import nds2  # noqa
except ImportError:
    logger.warning(
        "You do not have nds2 (python-nds2-client) installed. You may "
        " experience problems accessing interferometer data."
    )

try:
    import LDAStools.frameCPP  # noqa
except ImportError:
    logger.warning(
        "You do not have LDAStools.frameCPP (python-ldas-tools-framecpp) "
        "installed. You may experience problems accessing interferometer data."
    )


class DataGenerationInput(Input):
    """ Handles user-input and creation of intermediate interferometer list

    Parameters
    ----------
    parser: configargparse.ArgParser, optional
        The parser containing the command line / ini file inputs
    args_list: list, optional
        A list of the arguments to parse. Defaults to `sys.argv[1:]`
    create_data: bool
        If false, no data is generated (used for testing)

    """

    def __init__(self, args, unknown_args, create_data=True):

        logger.info("Command line arguments: {}".format(args))
        logger.info("Unknown command line arguments: {}".format(unknown_args))

        # Generic initialisation
        self.meta_data = dict(
            command_line_args=args.__dict__,
            unknown_command_line_args=unknown_args,
            injection_parameters=None,
            bilby_version=bilby.__version__,
            bilby_pipe_version=get_version_information(),
        )
        self.injection_parameters = None

        # Admin arguments
        self.ini = args.ini
        self.cluster = args.cluster
        self.process = args.process

        # Run index arguments
        self.idx = args.idx
        self.generation_seed = args.generation_seed
        self.trigger_time = args.trigger_time

        # Naming arguments
        self.outdir = args.outdir
        self.label = args.label

        # Prior arguments
        self.prior_file = args.prior_file
        self.prior_dict = args.prior_dict
        self.deltaT = args.deltaT
        self.default_prior = args.default_prior

        # Data arguments
        self.ignore_gwpy_data_quality_check = args.ignore_gwpy_data_quality_check
        self.detectors = args.detectors
        self.channel_dict = args.channel_dict
        self.data_dict = args.data_dict
        self.data_format = args.data_format
        self.tukey_roll_off = args.tukey_roll_off
        self.zero_noise = args.zero_noise

        if args.timeslide_file is not None:
            self.gps_file = args.gps_file
            self.timeslide_file = args.timeslide_file
            self.timeslide_dict = self.get_timeslide_dict(self.idx)

        # Data duration arguments
        self.duration = args.duration
        self.post_trigger_duration = args.post_trigger_duration

        # Frequencies
        self.sampling_frequency = args.sampling_frequency
        self.minimum_frequency = args.minimum_frequency
        self.maximum_frequency = args.maximum_frequency
        self.reference_frequency = args.reference_frequency

        # Waveform, source model and likelihood
        self.waveform_generator_class = args.waveform_generator
        self.waveform_approximant = args.waveform_approximant
        self.catch_waveform_errors = args.catch_waveform_errors
        self.pn_spin_order = args.pn_spin_order
        self.pn_tidal_order = args.pn_tidal_order
        self.pn_phase_order = args.pn_phase_order
        self.pn_amplitude_order = args.pn_amplitude_order
        self.injection_waveform_approximant = args.injection_waveform_approximant
        self.frequency_domain_source_model = args.frequency_domain_source_model
        self.likelihood_type = args.likelihood_type
        self.extra_likelihood_kwargs = args.extra_likelihood_kwargs

        # PSD
        self.psd_maximum_duration = args.psd_maximum_duration
        self.psd_dict = args.psd_dict
        if self.psd_dict is None:
            self.psd_length = args.psd_length
            self.psd_fractional_overlap = args.psd_fractional_overlap
            self.psd_start_time = args.psd_start_time
            self.psd_method = args.psd_method

        # ROQ
        self.roq_folder = args.roq_folder
        self.roq_scale_factor = args.roq_scale_factor

        # Calibration
        self.calibration_model = args.calibration_model
        self.spline_calibration_envelope_dict = args.spline_calibration_envelope_dict
        self.spline_calibration_amplitude_uncertainty_dict = (
            args.spline_calibration_amplitude_uncertainty_dict
        )
        self.spline_calibration_phase_uncertainty_dict = (
            args.spline_calibration_phase_uncertainty_dict
        )
        self.spline_calibration_nodes = args.spline_calibration_nodes

        # Marginalization
        self.distance_marginalization = args.distance_marginalization
        self.distance_marginalization_lookup_table = (
            args.distance_marginalization_lookup_table
        )
        self.phase_marginalization = args.phase_marginalization
        self.time_marginalization = args.time_marginalization
        self.jitter_time = args.jitter_time

        # Plotting
        self.create_plots = args.create_plots

        if create_data:
            self.create_data(args)

    def create_data(self, args):
        """ Function to iterarate through data generation method

        Note, the data methods are mutually exclusive and only one can be given to
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
        self.injection = args.injection
        self.injection_numbers = args.injection_numbers
        self.injection_file = args.injection_file
        self.injection_dict = args.injection_dict
        self.gaussian_noise = args.gaussian_noise

        # The following are all mutually exclusive methods to set the data
        if self.gaussian_noise:
            if args.injection_file is not None:
                logger.debug("Using provided injection file")
                self._set_interferometers_from_injection_in_gaussian_noise()
            elif args.injection_dict is not None:
                logger.debug("Using provided injection dict")
                self._set_interferometers_from_injection_in_gaussian_noise()
            elif args.injection is False:
                self._set_interferometers_from_gaussian_noise()
            else:
                raise BilbyPipeError("Unable to set data: no injection file")
        else:
            self._set_interferometers_from_data()

        if self.data_set is False:
            raise BilbyPipeError("Unable to set data")

    @property
    def generation_seed(self):
        return self._generation_seed

    @generation_seed.setter
    def generation_seed(self, generation_seed):
        """Sets the generation seed.

        If no generation seed has been provided, a random seed between 1 and 1e6 is
        selected.

        If a seed is provided, it is used as the base seed and all generation jobs will
        have their seeds set as {generation_seed = base_seed + job_idx}.

        NOTE: self.idx must not be None

        Parameters
        ----------
        generation_seed: int or None

        """
        if generation_seed is None:
            generation_seed = np.random.randint(1, 1e6)
        else:
            assert self.idx is not None
            generation_seed = generation_seed + self.idx
        self._generation_seed = generation_seed
        np.random.seed(generation_seed)
        logger.info("Generation seed set to {}".format(generation_seed))

    @property
    def injection_parameters(self):
        return self._injection_parameters

    @injection_parameters.setter
    def injection_parameters(self, injection_parameters):
        self._injection_parameters = injection_parameters
        if self.calibration_prior is not None:
            for key in self.calibration_prior:
                if key not in injection_parameters:
                    if "frequency" in key:
                        injection_parameters[key] = self.calibration_prior[key].peak
                    else:
                        injection_parameters[key] = 0
        self.meta_data["injection_parameters"] = injection_parameters

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

        else:
            raise BilbyPipeError("Unable to set psd_length={}".format(psd_length))

    @property
    def psd_duration(self):
        return self._psd_duration

    @psd_duration.setter
    def psd_duration(self, psd_duration):
        MAXIMUM = self.psd_maximum_duration
        if psd_duration <= MAXIMUM:
            self._psd_duration = psd_duration
            logger.info(
                "PSD duration set to {}s, {}x the duration {}s".format(
                    psd_duration, self.psd_length, self.duration
                )
            )
        else:
            self._psd_duration = MAXIMUM
            logger.info(
                "Requested PSD duration {}={}x{} exceeds allowed maximum {}"
                ". Setting psd_duration = {}".format(
                    psd_duration,
                    self.psd_length,
                    self.duration,
                    MAXIMUM,
                    self.psd_duration,
                )
            )

    @property
    def psd_start_time(self):
        """ The PSD start time relative to segment start time """
        if self._psd_start_time is not None:
            return self._psd_start_time
        elif self.trigger_time is not None:
            psd_start_time = -self.psd_duration
            logger.info(
                "Using default PSD start time {} relative to start time".format(
                    psd_start_time
                )
            )
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
    def parameter_conversion(self):
        if "binary_neutron_star" in self.frequency_domain_source_model:
            return bilby.gw.conversion.convert_to_lal_binary_neutron_star_parameters
        elif "binary_black_hole" in self.frequency_domain_source_model:
            return bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters
        else:
            return None

    @property
    def data_dict(self):
        return self._data_dict

    @data_dict.setter
    def data_dict(self, data_dict):
        if data_dict is None:
            logger.debug("data-dict set to None")
            self._data_dict = None
        elif isinstance(data_dict, str):
            self._data_dict = convert_string_to_dict(data_dict, "data-dict")
        elif isinstance(data_dict, dict):
            self._data_dict = data_dict
        else:
            raise BilbyPipeError("Input data-dict={} not understood".format(data_dict))

    @property
    def channel_dict(self):
        return self._channel_dict

    @channel_dict.setter
    def channel_dict(self, channel_dict):
        if channel_dict is not None:
            self._channel_dict = convert_string_to_dict(channel_dict, "channel-dict")
        else:
            logger.debug("channel-dict set to None")
            self._channel_dict = None

    def get_channel_type(self, det):
        """ Help method to read the channel_dict and print useful messages """
        if self.channel_dict is None:
            raise BilbyPipeError("No channel-dict argument provided")
        if det in self.channel_dict:
            return self.channel_dict[det]
        else:
            raise BilbyPipeError(
                "Detector {} not given in the channel-dict".format(det)
            )

    @property
    def sampling_frequency(self):
        return self._sampling_frequency

    @sampling_frequency.setter
    def sampling_frequency(self, sampling_frequency):
        if is_a_power_of_2(sampling_frequency) is False:
            logger.warning(
                "Sampling frequency {} not a power of 2, this can cause problems".format(
                    sampling_frequency
                )
            )
        self._sampling_frequency = sampling_frequency

    @property
    def trigger_time(self):
        return self._trigger_time

    @trigger_time.setter
    def trigger_time(self, trigger_time):
        self._trigger_time = trigger_time

    def _set_interferometers_from_gaussian_noise(self):
        """ Method to generate the interferometers data from Gaussian noise """

        ifos = bilby.gw.detector.InterferometerList(self.detectors)

        if self.psd_dict is not None:
            for ifo in ifos:
                if ifo.name in self.psd_dict.keys():
                    self._set_psd_from_file(ifo)

        if self.zero_noise:
            ifos.set_strain_data_from_zero_noise(
                sampling_frequency=self.sampling_frequency,
                duration=self.duration,
                start_time=self.start_time,
            )
        else:
            ifos.set_strain_data_from_power_spectral_densities(
                sampling_frequency=self.sampling_frequency,
                duration=self.duration,
                start_time=self.start_time,
            )

        self.interferometers = ifos

    def _set_interferometers_from_injection_in_gaussian_noise(self):
        """ Method to generate the interferometers data from an injection in Gaussian noise """

        self.injection_parameters = self.injection_df.iloc[self.idx].to_dict()
        logger.info("Injecting waveform with ")
        for prop in [
            "minimum_frequency",
            "maximum_frequency",
            "trigger_time",
            "start_time",
            "duration",
        ]:
            logger.info("{} = {}".format(prop, getattr(self, prop)))

        self._set_interferometers_from_gaussian_noise()

        waveform_arguments = self.get_injection_waveform_arguments()
        logger.info("Using waveform arguments: {}".format(waveform_arguments))
        waveform_generator = self.waveform_generator_class(
            duration=self.duration,
            start_time=self.start_time,
            sampling_frequency=self.sampling_frequency,
            frequency_domain_source_model=self.bilby_frequency_domain_source_model,
            parameter_conversion=self.parameter_conversion,
            waveform_arguments=waveform_arguments,
        )

        self.interferometers.inject_signal(
            waveform_generator=waveform_generator, parameters=self.injection_parameters
        )

    def inject_signal_into_time_domain_data(self, data, ifo):
        """ Method to inject a signal into time-domain interferometer data

        Parameters of the injection are obtained from the `injection_parameters` or
        the injection file (if injection_parameters has not been set).

        The geocent_time of the injection is set to be trigger_time +/- deltaT/2 if
        the geocent_time is not provided in the injection parameters.

        Parameters
        ----------
        data: gwpy.timeseries.TimeSeries
            The data into which to inject the signal
        ifo: bilby.gw.detector.Interferometer
            The interferometer for which the data relates to

        Returns
        -------
        data_and_signal: gwpy.timeseries.TimeSeries
            The data with the signal added

        """

        # Get the injection parameters
        if self.injection_parameters is not None:
            parameters = self.injection_parameters
        else:
            parameters = self.injection_df.iloc[self.idx].to_dict()
            self.injection_parameters = parameters

        # Set the geocent time if none is provided
        if "geocent_time" not in parameters:
            parameters["geocent_time"] = get_geocent_time_with_uncertainty(
                geocent_time=self.trigger_time, uncertainty=self.deltaT / 2.0
            )

        waveform_arguments = self.get_injection_waveform_arguments()

        waveform_generator = self.waveform_generator_class(
            duration=self.duration,
            sampling_frequency=self.sampling_frequency,
            frequency_domain_source_model=self.bilby_frequency_domain_source_model,
            parameter_conversion=self.parameter_conversion,
            waveform_arguments=waveform_arguments,
        )

        if self.create_plots:
            outdir = self.data_directory
            label = self.label
        else:
            outdir = None
            label = None

        logger.info("Injecting with {}".format(self.injection_waveform_approximant))
        (
            signal_and_data,
            meta_data,
        ) = bilby.gw.detector.inject_signal_into_gwpy_timeseries(
            data=data,
            waveform_generator=waveform_generator,
            parameters=parameters,
            det=ifo.name,
            outdir=outdir,
            label=label,
        )
        ifo.meta_data = meta_data

        if self.create_plots:
            # Plots of before and after injection saved
            plot_kwargs = dict(
                det=ifo.name,
                data_directory=self.data_directory,
                trigger_time=self.trigger_time,
                duration=self.duration,
                post_trigger_duration=self.post_trigger_duration,
                label=self.label,
            )

            strain_spectogram_plot(
                data=data, extra_label="before_injection", **plot_kwargs
            )
            strain_spectogram_plot(
                data=signal_and_data, extra_label="with_injection", **plot_kwargs
            )

        return signal_and_data

    @property
    def psd_dict(self):
        return self._psd_dict

    @psd_dict.setter
    def psd_dict(self, psd_dict):
        if psd_dict is not None:
            self._psd_dict = convert_string_to_dict(psd_dict, "psd-dict")
        else:
            logger.debug("psd-dict set to None")
            self._psd_dict = None

    def _set_psd_from_file(self, ifo):
        psd_file = self.psd_dict[ifo.name]
        logger.info("Setting {} PSD from file {}".format(ifo.name, psd_file))
        ifo.power_spectral_density = PowerSpectralDensity.from_power_spectral_density_file(
            psd_file=psd_file
        )

    def _set_interferometers_from_data(self):
        """ Method to generate the interferometers data from data"""
        end_time = self.start_time + self.duration
        roll_off = self.tukey_roll_off
        if 2 * roll_off > self.duration:
            raise ValueError("2 * tukey-roll-off is longer than segment duration.")
        ifo_list = []
        for det in self.detectors:
            logger.info("Getting analysis-segment data for {}".format(det))
            data = self._get_data(
                det, self.get_channel_type(det), self.start_time, end_time
            )
            ifo = bilby.gw.detector.get_empty_interferometer(det)
            ifo.strain_data.roll_off = roll_off
            if self.injection_file is not None:
                data = self.inject_signal_into_time_domain_data(data, ifo)
            ifo.strain_data.set_from_gwpy_timeseries(data)

            if self.psd_dict is not None and det in self.psd_dict:
                psd_data = None
                self._set_psd_from_file(ifo)
            else:
                logger.info("Setting PSD for {} from data".format(det))
                psd_data = self.__get_psd_data(det)
                psd = self.__generate_psd(psd_data, roll_off)
                ifo.power_spectral_density = PowerSpectralDensity(
                    frequency_array=psd.frequencies.value, psd_array=psd.value
                )

            if self.create_plots:
                self.__plot_ifo_data(det, strain_data=data, psd_strain_data=psd_data)

            ifo_list.append(ifo)

        self.interferometers = bilby.gw.detector.InterferometerList(ifo_list)

    def __get_psd_data(self, det):
        # psd_start_time is given relative to the segment start time
        # so here we calculate the actual start time
        actual_psd_start_time = self.start_time + self.psd_start_time
        actual_psd_end_time = actual_psd_start_time + self.psd_duration
        logger.info("Getting psd-segment data for {}".format(det))
        psd_data = self._get_data(
            det, self.get_channel_type(det), actual_psd_start_time, actual_psd_end_time
        )
        return psd_data

    def __generate_psd(self, psd_data, roll_off):
        """Create the psd from strain data."""
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
        return psd

    def __plot_ifo_data(self, det, strain_data, psd_strain_data=None):
        """Method to plot an IFO's data.

        Parameters
        ----------
        det: str
            The detector name corresponding to the key in data-dict
        strain_data, psd_strain_data: gwpy.TimeSeries
            The timeseries strain data of a detector.

        Returns
        -------
        None

        File by the name `<outdir>/data/<det>_<Label>_D{duration}_data.png`
        is saved
        """
        if psd_strain_data is None:
            logger.info("Unable to plot the IFO data without the PSD data")
            return
        else:
            plot_psd = True

        plot_kwargs = dict(
            det=det,
            data_directory=self.data_directory,
            trigger_time=self.trigger_time,
            duration=self.duration,
            post_trigger_duration=self.post_trigger_duration,
            label=self.label,
        )

        time = [strain_data.t0.value, strain_data.t0.value + strain_data.duration.value]
        psd_time = [
            psd_strain_data.t0.value,
            psd_strain_data.t0.value + psd_strain_data.duration.value,
        ]

        # plot PSD
        if plot_psd:
            strain_spectogram_plot(
                data=psd_strain_data,
                extra_label="D{}".format(int(psd_time[1] - psd_time[0])),
                **plot_kwargs,
            )

        # plot psd_strain_data+strain_data  and zoom into strain_data segment
        data_with_psd = psd_strain_data.append(strain_data, inplace=False)
        strain_spectogram_plot(
            data=data_with_psd,
            extra_label="D{}".format(int(time[1] - time[0])),
            **plot_kwargs,
        )

    def _get_data(self, det, channel_type, start_time, end_time, resample=True):
        """ Read in data using gwpy

        This first uses the `gwpy.timeseries.TimeSeries.get()` method to access
        the data, if this fails, it then attempts to use `fetch_open_data()` as
        a fallback.

        Parameters
        ----------
        channel_type: str
            The full channel name is formed from <det>:<channel_type>, see
            bilby_pipe_generation --help for more information. If given as a
            list each type will be tried and the first success returned.
        start_time, end_time: float
            GPS start and end time of segment
        """
        timeslide_val = None
        if hasattr(self, "timeslide_dict"):
            timeslide_val = self.timeslide_dict[det]
            start_time = start_time + timeslide_val
            end_time = end_time + timeslide_val
            logger.info(
                "Applying timeshift of {}. Time range {} - {} => {} - {}".format(
                    timeslide_val,
                    start_time - timeslide_val,
                    end_time - timeslide_val,
                    start_time,
                    end_time,
                )
            )

        if self.ignore_gwpy_data_quality_check is False:
            data_is_good = self._is_gwpy_data_good(start_time, end_time, det)
            if not data_is_good:
                raise BilbyPipeError("Data quality is not good.")

        data = None
        channel = "{}:{}".format(det, channel_type)
        if data is None and self.data_dict is not None:
            data = self._gwpy_read(det, channel, start_time, end_time)
        if data is None:
            data = self._gwpy_get(channel, start_time, end_time)
        if data is None:
            data = self._gwpy_fetch_open_data(det, start_time, end_time)

        if resample and data.sample_rate.value == self.sampling_frequency:
            logger.info("Sample rate matches data no resampling")
        elif resample:
            logger.info(
                "Resampling data to sampling_frequency {}".format(
                    self.sampling_frequency
                )
            )
            data = data.resample(self.sampling_frequency)
        else:
            logger.info("No data resampling requested")

        if timeslide_val:
            # to match up the time axis for the interferometer network
            data.shift(-timeslide_val)

        return data

    @staticmethod
    def _is_gwpy_data_good(start_time, end_time, det):
        """Check if start-end time is a period when the IFO has quality data.

        Check passes if the IFO has quality data during the time period provided.

        Note: we are using the DMT-SCIENCE channel to check the quality.
        https://labcit.ligo.caltech.edu/~jzweizig/talks/LSC-2009-06-03/DMT-DQ_Stat-2009-06-03.pdf

        This method is slow as it queries GWpy.

        Parameters
        ----------
        start_time, end_time: float
            GPS start and end time of required data.
        det: str
            The string key that represents the detector ("H1", "L1", etc)

        Returns
        -------

        True: if data is good (IFO has quality data during entire duration).
        False: if data is bad (IFO does not have quality data during entire duration).
        None: if the data quality check failed

        """
        # Create data quality flag
        channel_num = 1
        quality_flag = f"{det}:DMT-SCIENCE:{channel_num}"
        logger.info(
            "Checking data quality {} {}-{}"
            "".format(quality_flag, start_time, end_time)
        )
        try:
            flag = gwpy.segments.DataQualityFlag.query(
                flag=quality_flag, start=start_time, stop=end_time
            )

            # compare active duration from quality flag and total duration
            total_duration = end_time - start_time
            active_duration = (
                flag.livetime.gpsSeconds + flag.livetime.gpsNanoSeconds * 1e-9
            )
            inactive_duration = total_duration - active_duration

            # data is not good if there is any period when the IFO is inactive
            if inactive_duration > 0:
                data_is_good = False
                logger.warning(
                    "Data quality check: FAILED. \n"
                    "{det} does not have quality data for "
                    "{inactive_duration}s out of {total_duration}s".format(
                        det=det,
                        inactive_duration=inactive_duration,
                        total_duration=total_duration,
                    )
                )
            else:
                data_is_good = True
                logger.info("Data quality check: PASSED.")
        except Exception as e:
            logger.warning("Error in Data Quality Check: {}.".format(e))
            data_is_good = None

        return data_is_good

    def _gwpy_read(self, det, channel, start_time, end_time, dtype="float64"):
        """ Wrapper function to gwpy.timeseries.TimeSeries.read()

        Parameters
        ----------
        det: str
            The detector name corresponding to the key in data-dict
        channel: str
            The name of the channel to read, e.g. 'L1:GDS-CALIB_STRAIN'
        start_time, end_time: float
            GPS start and end time of required data
        dtype: str or np.dtype
            Data type requested

        Returns
        -------
        data: TimeSeries
            If successful, the data, otherwise None is returned

        """

        logger.debug("data-dict provided, attempt read of data")

        if det not in self.data_dict:
            logger.info("Detector {} not found in data-dict".format(det))
            return None
        else:
            source = self.data_dict[det]
            format_ext = os.path.splitext(source)[1]

        if "gwf" in format_ext:
            kwargs = dict(
                source=source,
                channel=channel,
                start=start_time,
                end=end_time,
                dtype=dtype,
                format="gwf.lalframe",
            )
        elif "hdf5" in format_ext:
            kwargs = dict(source=source, start=start_time, end=end_time, format="hdf5")
        elif "txt" in format_ext:
            data = kwargs = dict(source=source)
        else:
            # Generic best try
            kwargs = dict(
                source=source, channel=channel, start=start_time, end=end_time
            )

        if self.data_format is not None:
            kwargs["format"] = self.data_format

        try:
            kwargs_string = ""
            for key, val in kwargs.items():
                if isinstance(val, str):
                    val = "'{}'".format(val)
                kwargs_string += "{}={}, ".format(key, val)
            logger.info(
                "Running: gwpy.timeseries.TimeSeries.read({})".format(kwargs_string)
            )
            data = gwpy.timeseries.TimeSeries.read(**kwargs)

            if data.duration.value < end_time - start_time:
                logger.warning(
                    "Unable to read in requested {}s duration of data from {}"
                    " only {}s available: returning None".format(
                        end_time - start_time, source, data.duration.value
                    )
                )
                data = None
            elif data.duration.value > end_time - start_time:
                logger.info(
                    "Read in {}s of data from {}, but {}s requested, truncating".format(
                        data.duration.value, source, end_time - start_time
                    )
                )
                data = data[data.times.value >= start_time]
                data = data[data.times.value < end_time]

            return data
        except ValueError as e:
            logger.info("Reading of data failed with error {}".format(e))
            return None

    def _gwpy_get(self, channel, start_time, end_time, dtype="float64"):
        """ Wrapper function to gwpy.timeseries.TimeSeries.get()

        Parameters
        ----------
        channel: str
            The name of the channel to read, e.g. 'L1:GDS-CALIB_STRAIN'
        start_time, end_time: float
            GPS start and end time of required data
        dtype: str or np.dtype
            Data type requested

        Returns
        -------
        data: TimeSeries
            If successful, the data, otherwise None is returned

        """
        logger.debug("Attempt to locate data")
        logger.info(
            "Calling TimeSeries.get('{}', start={}, end={}, dtype='{}')".format(
                channel, start_time, end_time, dtype
            )
        )
        if self.data_format:
            kwargs = dict(format=self.data_format)
            logger.info("Extra kwargs passed to get(): {}".format(kwargs))
        else:
            kwargs = dict()
        try:
            data = gwpy.timeseries.TimeSeries.get(
                channel, start_time, end_time, verbose=False, dtype=dtype, **kwargs
            )
            return data
        except RuntimeError as e:
            logger.info("Unable to read data for channel {}".format(channel))
            logger.debug("Error message {}".format(e))
        except ImportError:
            logger.info("Unable to read data as NDS2 is not installed")
        except TypeError:
            logger.debug("Problem reading data try again without kwargs")
            data = gwpy.timeseries.TimeSeries.get(
                channel, start_time, end_time, verbose=False, dtype=dtype
            )
            return data

    def _gwpy_fetch_open_data(self, det, start_time, end_time):
        """ Wrapper function to gwpy.timeseries.TimeSeries.fetch_open_data()

        Parameters
        ----------
        det: str
            The detector name, e.g 'H1'
        start_time, end_time: float
            GPS start and end time of required data

        Returns
        -------
        data: TimeSeries
            If successful, the data, otherwise None is returned

        """

        logger.info(
            "Previous attempts to download data failed, trying with `fetch_open_data`"
        )
        logger.info(
            "Calling TimeSeries.fetch_open_data('{}', start={}, end={})".format(
                det, start_time, end_time
            )
        )
        data = gwpy.timeseries.TimeSeries.fetch_open_data(det, start_time, end_time)
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

    def add_calibration_model_to_interferometers(self, ifo):
        if self.calibration_model == "CubicSpline":
            ifo.calibration_model = bilby.gw.calibration.CubicSpline(
                prefix="recalib_{}_".format(ifo.name),
                minimum_frequency=ifo.minimum_frequency,
                maximum_frequency=ifo.maximum_frequency,
                n_points=self.spline_calibration_nodes,
            )
        else:
            raise BilbyPipeError(
                "calibration model {} not implemented".format(self.calibration_model)
            )

    @interferometers.setter
    def interferometers(self, interferometers):
        for ifo in interferometers:
            if isinstance(ifo, bilby.gw.detector.Interferometer) is False:
                raise BilbyPipeError("ifo={} is not a bilby Interferometer".format(ifo))
            if self.minimum_frequency is not None:
                ifo.minimum_frequency = self.minimum_frequency_dict[ifo.name]
            if self.maximum_frequency is not None:
                ifo.maximum_frequency = self.maximum_frequency_dict[ifo.name]
            if self.calibration_model is not None:
                self.add_calibration_model_to_interferometers(ifo)

        self._interferometers = interferometers
        self.data_set = True
        if self.create_plots:
            interferometers.plot_data(outdir=self.data_directory, label=self.label)

    def save_data_dump(self):
        """ Method to dump the saved data to disk for later analysis """
        likelihood = self.likelihood
        if self.distance_marginalization:
            likelihood_lookup_table = dict(
                np.load(likelihood.cached_lookup_table_filename)
            )
        else:
            likelihood_lookup_table = None
        data_dump = DataDump(
            outdir=self.data_directory,
            label=self.label,
            idx=self.idx,
            trigger_time=self.trigger_time,
            interferometers=self.interferometers,
            meta_data=self.meta_data,
            likelihood_lookup_table=likelihood_lookup_table,
            likelihood_roq_weights=getattr(likelihood, "weights", None),
            likelihood_roq_params=getattr(likelihood, "roq_params", None),
            priors_dict=dict(self.priors),
            priors_class=self.priors.__class__,
        )
        data_dump.to_pickle()

    def save_roq_weights(self):
        logger.info(
            "Using ROQ likelihood with roq-folder={} and roq-scale-factor={}".format(
                self.roq_folder, self.roq_scale_factor
            )
        )

        params = np.genfromtxt(self.roq_folder + "/params.dat", names=True)

        freq_nodes_linear = np.load(self.roq_folder + "/fnodes_linear.npy")
        freq_nodes_quadratic = np.load(self.roq_folder + "/fnodes_quadratic.npy")
        freq_nodes_linear *= self.roq_scale_factor
        freq_nodes_quadratic *= self.roq_scale_factor

        basis_matrix_linear = np.load(self.roq_folder + "/B_linear.npy").T
        basis_matrix_quadratic = np.load(self.roq_folder + "/B_quadratic.npy").T

        waveform_arguments = self.get_default_waveform_arguments()
        waveform_arguments["frequency_nodes_linear"] = freq_nodes_linear
        waveform_arguments["frequency_nodes_quadratic"] = freq_nodes_quadratic

        waveform_generator = self.waveform_generator_class(
            sampling_frequency=self.interferometers.sampling_frequency,
            duration=self.interferometers.duration,
            frequency_domain_source_model=self.bilby_roq_frequency_domain_source_model,
            parameter_conversion=self.parameter_conversion,
            start_time=self.interferometers.start_time,
            waveform_arguments=waveform_arguments,
        )

        likelihood = bilby.gw.likelihood.ROQGravitationalWaveTransient(
            interferometers=self.interferometers,
            priors=self.priors,
            roq_params=params,
            roq_scale_factor=self.roq_scale_factor,
            waveform_generator=waveform_generator,
            linear_matrix=basis_matrix_linear,
            quadratic_matrix=basis_matrix_quadratic,
        )

        del basis_matrix_linear, basis_matrix_quadratic

        if self.injection_parameters is not None:
            likelihood.parameters.update(self.injection_parameters)
            logger.info(
                "ROQ likelihood at injection values = "
                "{}".format(likelihood.log_likelihood_ratio())
            )

        weight_file = os.path.join(self.data_directory, self.label + "_roq_weights.npz")
        self.meta_data["weight_file"] = weight_file
        likelihood.save_weights(weight_file)


def create_generation_parser():
    return create_parser(top_level=False)


def main():
    args, unknown_args = parse_args(sys.argv[1:], create_generation_parser())
    log_version_information()
    data = DataGenerationInput(args, unknown_args)
    if args.likelihood_type == "ROQGravitationalWaveTransient":
        data.save_roq_weights()
    data.save_data_dump()
    logger.info("Completed data generation")
