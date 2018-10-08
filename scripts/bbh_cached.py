#!/usr/bin/env python
"""
"""
from __future__ import division, print_function
import numpy as np
import logging
import sys
import argparse
from glob import glob

from bilby import run_sampler
from bilby.core.utils import setup_logger, command_line_parser
from bilby.core.prior import Uniform
from bilby.gw.waveform_generator import WaveformGenerator
from bilby.gw.source import lal_binary_black_hole
from bilby.gw.conversion import (
    convert_to_lal_binary_black_hole_parameters, generate_all_bbh_parameters)
from bilby.gw.detector import InterferometerList
from bilby.gw.prior import BBHPriorSet
from bilby.gw.likelihood import GravitationalWaveTransient
from bilby_pipe.utils import load_data_from_cache_file


# parse arguments
parser = argparse.ArgumentParser(parents=[command_line_parser],
                                 fromfile_prefix_chars='@')
parser.add_argument("--trigger_time", type=float, help="Trigger time",
                    required=True)
parser.add_argument("--frame_caches", default=None, nargs="*",
                    help="Cache files containing information about frames",
                    required=True)
parser.add_argument("-p", "--prior_file", default=None, help="prior file")
parser.add_argument("--channel_names", default=None, nargs="*",
                    help="Channel names to use, if not provided known "
                    "channel names will be tested.")
parser.add_argument('--psd_duration', default=500, type=int,
                    help='Time used to generate the PSD, default is 500.')
parser.add_argument('--dist-marg', dest='distance', action='store_true', default=False)
parser.add_argument('--phase-marg', dest='phase', action='store_true', default=True)
parser.add_argument('--time-marg', dest='time', action='store_true', default=True)
parser.add_argument('--outdir', default='outdir', help='Output directory')
args = parser.parse_args()

prior_file = args.prior_file

setup_logger(log_level="info")

logging.info(sys.argv)

if args.distance:
    logging.info('Running with distance marginalisation.')
if args.time:
    logging.info('Running with time marginalisation.')
if args.phase:
    logging.info('Running with phase marginalisation.')

duration = 4.
sampling_frequency = 4096.

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
if args.frame_caches is not None:
    if args.channel_names is None:
        args.channel_names = [None]*len(args.frame_caches)
    for cache_file, channel_name in zip(args.frame_caches, args.channel_names):
        ifos.append(load_data_from_cache_file(
            cache_file, args.trigger_time, duration, args.psd_duration,
            channel_name))
else:
    raise Exception("Cannot find any data!")

# Set up prior
priors = BBHPriorSet(filename=prior_file)
priors['geocent_time'] = Uniform(
        minimum=args.trigger_time - 0.1, maximum=args.trigger_time + 0.1,
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
            ''.join([ifo.name for ifo in ifos]), args.trigger_time),
        nlive=500, outdir=args.outdir,
        conversion_function=generate_all_bbh_parameters)
