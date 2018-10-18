#!/usr/bin/env python
"""
A collection of classes and functions useful for generating scripts
"""

import numpy as np
import configargparse
import sys

from bilby.core.utils import logger
import bilby


def create_default_parser():
    """ Generate a parser with typical command line arguments

    Additional options can be added to the returned parser beforing calling
    `parser.parse_args` to generate the arguments`

    Returns
    -------
    parser: configargparse.ArgParser
        A parser with all the default options already added

    """
    parser = configargparse.ArgParser(ignore_unknown_config_file_keys=True)
    parser.add('--ini', is_config_file=True, help='The ini-style config file')
    parser.add('--cluster', type=int,
               help='The condor cluster ID', default=None)
    parser.add('--process', type=int,
               help='The condor process ID', default=None)
    parser.add(
        '--detectors', action='append',
        help=('The names of detectors to include. If given in the ini file, '
              'multiple detectors are specified by `detectors=[H1, L1]`. If '
              'given at the command line, as `--detectors H1 --detectors L1`'))
    parser.add('--calibration', type=int, default=2,
               help='Which calibration to use')
    parser.add('--duration', type=int, default=4,
               help='The duration of data around the event to use')
    parser.add("--trigger-time", default=None, type=float,
               help="The trigger time")
    parser.add("--sampling-frequency", default=4096, type=int)
    parser.add("--channel-names", default=None, nargs="*",
               help="Channel names to use, if not provided known "
               "channel names will be tested.")
    parser.add('--psd-duration', default=500, type=int,
               help='Time used to generate the PSD, default is 500.')
    parser.add('--minimum-frequency', default=20, type=float)
    parser.add("--prior-file", default=None, help="prior file")
    parser.add("--deltaT", type=float, default=0.1,
               help=("The symmetric width (in s) around the trigger time to"
                     " search over the coalesence time"))
    parser.add('--reference-frequency', default=20, type=float,
               help="The reference frequency")
    parser.add('--waveform-approximant', default='IMRPhenomPv2', type=str,
               help="Name of the waveform approximant")
    parser.add(
        '--distance-marginalization', action='store_true', default=False,
        help='If true, use a distance-marginalized likelihood')
    parser.add(
        '--phase-marginalization', action='store_true', default=False,
        help='If true, use a phase-marginalized likelihood')
    parser.add(
        '--time-marginalization', action='store_true', default=False,
        help='If true, use a time-marginalized likelihood')
    parser.add('--sampler', default=None)
    parser.add('--sampler-kwargs', default=None)
    parser.add('--outdir', default='outdir', help='Output directory')
    parser.add('--label', default='label', help='Output label')
    parser.add('--sampling-seed', default=None, type=int, help='Random sampling seed')
    return parser


class ScriptInput(object):
    def __init__(self, parser=None, args_list=None):
        """ An object to hold all the inputs to the script

        Parameters
        ----------
        parser: configargparse.ArgParser, optional
            The parser containing the command line / ini file inputs. If not
            given, then `bilby_pipe.script_helper.create_default_parser()` is
            used.

        """

        if args_list is None:
            args_list = sys.argv[1:]

        if parser is None:
            parser = create_default_parser()

        args, unknown_args = parser.parse_known_args(args_list)

        logger.info('Command line arguments: {}'.format(args))

        self.unknown_args = unknown_args
        args_dict = vars(args)
        for key, value in args_dict.items():
            setattr(self, key, value)

    @property
    def minimum_frequency(self):
        return self._minimum_frequency

    @minimum_frequency.setter
    def minimum_frequency(self, minimum_frequency):
        self._minimum_frequency = float(minimum_frequency)

    @property
    def reference_frequency(self):
        return self._reference_frequency

    @reference_frequency.setter
    def reference_frequency(self, reference_frequency):
        self._reference_frequency = float(reference_frequency)

    @staticmethod
    def _convert_string_to_list(string):
        """ Converts various strings to a list """
        string = string.replace(',', ' ')
        string = string.replace('[', '')
        string = string.replace(']', '')
        string = string.replace('"', '')
        string = string.replace("'", '')
        string_list = string.split()
        return string_list

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
            raise ValueError('Input `detectors` = {} not understood'
                             .format(detectors))

        det_list.sort()
        det_list = [det.upper() for det in det_list]
        self._detectors = det_list

    @property
    def sampling_seed(self):
        return self._samplng_seed

    @sampling_seed.setter
    def sampling_seed(self, sampling_seed):
        if sampling_seed is None:
            sampling_seed = np.random.randint(1, 1e6)
        self._samplng_seed = sampling_seed
        np.random.seed(sampling_seed)
        logger.info('Sampling seed set to {}'.format(sampling_seed))

    @property
    def sampler_kwargs(self):
        if hasattr(self, '_sampler_kwargs'):
            return self._sampler_kwargs
        else:
            return None

    @sampler_kwargs.setter
    def sampler_kwargs(self, sampler_kwargs):
        if sampler_kwargs is not None:
            try:
                self._sampler_kwargs = eval(sampler_kwargs)
            except (NameError, TypeError) as e:
                raise ValueError(
                    "Error {}. Unable to parse sampler_kwargs: {}"
                    .format(e, sampler_kwargs))
        else:
            self._sampler_kwargs = None

    @property
    def ifos(self):
        if getattr(self, '_ifos', None) is None:
            ifos = bilby.gw.detector.InterferometerList([])
            if self.frame_caches is not None:
                if self.channel_names is None:
                    self.channel_names = [None] * len(self.frame_caches)
                for cache_file, channel_name in zip(self.frame_caches,
                                                    self.channel_names):
                    ifos.append(bilby.gw.detector.load_data_from_cache_file(
                        cache_file, self.trigger_time, self.duration,
                        self.psd_duration, channel_name))
                self._ifos = ifos
                return self._ifos
            else:
                raise Exception("Cannot find any data!")
        else:
            return self._ifos

    @ifos.setter
    def ifos(self, ifos):
        self._ifos = ifos

    @property
    def run_label(self):
        label = '{}_{}_{}'.format(
            self.label, ''.join(self.detectors), self.sampler)
        return label

    @property
    def priors(self):
        priors = bilby.gw.prior.BBHPriorSet(
            filename=self.prior_file)
        priors['geocent_time'] = bilby.core.prior.Uniform(
            minimum=self.trigger_time - self.deltaT / 2,
            maximum=self.trigger_time + self.deltaT / 2,
            name='geocent_time', latex_label='$t_c$', unit='$s$')
        return priors

    @property
    def parameter_conversion(self):
        return bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters

    @property
    def waveform_generator(self):
        waveform_generator = bilby.gw.WaveformGenerator(
            sampling_frequency=self.sampling_frequency, duration=self.duration,
            frequency_domain_source_model=self.frequency_domain_source_model,
            parameter_conversion=self.parameter_conversion,
            waveform_arguments=self.waveform_arguments)
        return waveform_generator

    @property
    def waveform_arguments(self):
        return dict(
            reference_frequency=self.reference_frequency,
            waveform_approximant=self.waveform_approximant,
            minimum_frequency=self.minimum_frequency)

    @property
    def likelihood(self):
        return bilby.gw.likelihood.GravitationalWaveTransient(
            interferometers=self.ifos,
            waveform_generator=self.waveform_generator, prior=self.priors,
            phase_marginalization=self.phase_marginalization,
            distance_marginalization=self.distance_marginalization,
            time_marginalization=self.time_marginalization)
