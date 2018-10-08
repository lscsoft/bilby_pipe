#!/usr/bin/env python
"""
"""
from __future__ import division, print_function
import numpy as np
import logging
import sys
import configargparse

import bilby
from bilby import run_sampler
from bilby.core.utils import setup_logger
from bilby.core.prior import Uniform
from bilby.gw.waveform_generator import WaveformGenerator
from bilby.gw.source import lal_binary_black_hole
from bilby.gw.conversion import (
    convert_to_lal_binary_black_hole_parameters, generate_all_bbh_parameters)
from bilby.gw.detector import InterferometerList
from bilby.gw.detector import load_data_from_cache_file
from bilby.gw.prior import BBHPriorSet
from bilby.gw.likelihood import GravitationalWaveTransient


parser = configargparse.ArgParser(ignore_unknown_config_file_keys=True)
parser.add('--ini', is_config_file=True)
parser.add('--gracedb', type=str, help='Gracedb UID')
parser.add('--detectors', nargs='+', default=['H1', 'L1'],
           help='The detector names, {H1, L1}')
parser.add('--calibration', type=int, default=2,
           help='Which calibration to use')
parser.add('--duration', type=int, default=4,
           help='The duration of data about the event to use')
parser.add("-p", "--prior_file", default=None, help="prior file")
parser.add("--channel_names", default=None, nargs="*",
           help="Channel names to use, if not provided known "
           "channel names will be tested.")
parser.add('--psd_duration', default=500, type=int,
           help='Time used to generate the PSD, default is 500.')
parser.add('--dist-marg', dest='distance', action='store_true', default=False)
parser.add('--phase-marg', dest='phase', action='store_true', default=True)
parser.add('--time-marg', dest='time', action='store_true', default=True)
parser.add('--outdir', default='outdir', help='Output directory')
args = parser.parse_args()

prior_file = args.prior_file
detectors = ' '.join(args.detectors).split(' ')  # Check to make sure is a list

setup_logger(log_level="info")
logging.info(sys.argv)

if args.distance:
    logging.info('Running with distance marginalisation.')
if args.time:
    logging.info('Running with time marginalisation.')
if args.phase:
    logging.info('Running with phase marginalisation.')

duration = args.duration
sampling_frequency = 4096.

candidate, frame_caches = bilby.gw.utils.get_gracedb(
    args.gracedb, args.outdir, duration, args.calibration, detectors)

trigger_time = candidate['gpstime']

# Create the waveform_generator using a LAL BinaryBlackHole source function
waveform_generator = WaveformGenerator(
    sampling_frequency=sampling_frequency, duration=duration,
    frequency_domain_source_model=lal_binary_black_hole,
    parameter_conversion=convert_to_lal_binary_black_hole_parameters,
    waveform_arguments={
        'reference_frequency': 20., 'waveform_approximant': 'IMRPhenomPv2',
        'minimum_frequency': 20.})

# Set up interferometers.
ifos = InterferometerList([])
if frame_caches is not None:
    if args.channel_names is None:
        args.channel_names = [None]*len(frame_caches)
    for cache_file, channel_name in zip(frame_caches, args.channel_names):
        ifos.append(load_data_from_cache_file(
            cache_file, trigger_time, duration, args.psd_duration,
            channel_name))
else:
    raise Exception("Cannot find any data!")

# Set up prior
priors = BBHPriorSet(filename=prior_file)
priors['geocent_time'] = Uniform(
        minimum=trigger_time - 0.1, maximum=trigger_time + 0.1,
        name='geocent_time', latex_label='$t_c$', unit='$s$')

likelihood = GravitationalWaveTransient(
    interferometers=ifos, waveform_generator=waveform_generator, prior=priors,
    phase_marginalization=args.phase, distance_marginalization=args.distance,
    time_marginalization=args.time)

sampling_seed = np.random.randint(1, 1e6)
np.random.seed(sampling_seed)
logging.info('Sampling seed is {}'.format(sampling_seed))

# Run sampler
result = run_sampler(
        likelihood=likelihood, priors=priors, sampler='dynesty',
        label='{}_{}'.format(
            ''.join([ifo.name for ifo in ifos]), trigger_time),
        nlive=500, outdir=args.outdir,
        conversion_function=generate_all_bbh_parameters)
