#!/usr/bin/env python
"""
A collection of classes and functions useful for generating scripts
"""

import numpy as np
import configargparse

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
    parser.add('--detectors', nargs='+', default=['H1', 'L1'],
               help='The names of detectors to include {H1, L1}')
    parser.add('--calibration', type=int, default=2,
               help='Which calibration to use')
    parser.add('--duration', type=int, default=4,
               help='The duration of data around the event to use')
    parser.add("--prior_file", default=None, help="prior file")
    parser.add("--deltaT", type=float, default=0.1,
               help=("The symmetric width (in s) around the trigger time to"
                     "search over the coalesence time"))
    parser.add("--sampling-frequency", default=4096, type=int)
    parser.add("--channel_names", default=None, nargs="*",
               help="Channel names to use, if not provided known "
               "channel names will be tested.")
    parser.add('--psd_duration', default=500, type=int,
               help='Time used to generate the PSD, default is 500.')
    parser.add('--reference_frequency', default=20, type=float)
    parser.add('--minimum-frequency', default=20, type=float)
    parser.add('--waveform_approximant', default='IMRPhenomPv2', type=str)
    parser.add('--distance-marginalization', action='store_true',
               default=False)
    parser.add('--phase-marginalization', action='store_true', default=True)
    parser.add('--time-marginalization', action='store_true', default=True)
    parser.add('--outdir', default='outdir', help='Output directory')
    parser.add('--label', default='outdir', help='Output label')
    parser.add('--sampler', default=None)
    parser.add('--sampler-kwargs', default=None)
    return parser


class ScriptInput(object):
    def __init__(self, args):
        """ An object to hold all the inputs to the script """

        logger.info('Command line arguments: {}'.format(args))

        sampling_seed = np.random.randint(1, 1e6)
        np.random.seed(sampling_seed)
        logger.info('Sampling seed is {}'.format(sampling_seed))

        args_dict = vars(args)
        for key, value in args_dict.items():
            setattr(self, key, value)

    @staticmethod
    def _split_string_by_space(string):
        """ Converts "H1 L1" to ["H1", "L1"] """
        return string.split(' ')

    @property
    def detectors(self):
        """ A list of the detectors to search over, e.g., ['H1', 'L1'] """
        return self._detectors

    @detectors.setter
    def detectors(self, detectors):
        if isinstance(detectors, str):
            det_list = self._split_string_by_space(detectors)
        elif isinstance(detectors, list):
            if len(detectors) == 1:
                det_list = self._split_string_by_space(detectors[0])
            else:
                det_list = detectors
        else:
            raise ValueError('Input `include_detectors` = {} not understood'
                             .format(detectors))

        det_list.sort()
        det_list = [det.upper() for det in det_list]
        self._detectors = det_list

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

    @property
    def run_label(self):
        label = '{}_{}_{}'.format(
            self.label, ''.join([ifo.name for ifo in self.ifos]),
            self.trigger_time)
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
