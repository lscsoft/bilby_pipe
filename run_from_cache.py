#!/usr/bin/env python
"""
"""
from __future__ import division, print_function
import numpy as np
import logging
import sys
# import os
# import deepdish
import argparse
from glob import glob
# import tupak
from tupak import run_sampler
from tupak.core.utils import setup_logger, command_line_parser
from tupak.core.prior import Uniform
from tupak.gw.waveform_generator import WaveformGenerator
from tupak.gw.source import lal_binary_black_hole
from tupak.gw.conversion import (
    convert_to_lal_binary_black_hole_parameters, generate_all_bbh_parameters)
from tupak.gw.detector import InterferometerList
from tupak.gw.prior import BBHPriorSet
from tupak.gw.likelihood import GravitationalWaveTransient
from bilby_pipe.utils import load_data_from_cache_file


# parse arguments
parser = argparse.ArgumentParser(parents=[command_line_parser])
parser.add_argument("-p", "--prior_file",
                    default=None, help="prior file")
parser.add_argument("--trigger_time", type=float, help="Trigger time")
parser.add_argument("--frame_caches", default=None, nargs="*",
                    help="Cache files containing information about frames.\n"
                    "If not provided '*.lcf' and '*.gwf' will be globbed.")
parser.add_argument("--channel_names", default=None, nargs="*",
                    help="Channel names to use, if not provided known "
                    "channel names will be tested.")
parser.add_argument('--psd_duration', default=500, type=int,
                    help='Time used to generate the PSD, default is 500.')
parser.add_argument('--dist-marg', dest='distance', action='store_true')
parser.add_argument('--no-dist-marg', dest='distance', action='store_false')
parser.add_argument('--phase-marg', dest='phase', action='store_true')
parser.add_argument('--no-phase-marg', dest='phase', action='store_false')
parser.add_argument('--time-marg', dest='time', action='store_true')
parser.add_argument('--no-time-marg', dest='time', action='store_false')
parser.set_defaults(time=True, phase=True, distance=False)
parser.add_argument('--outdir', default='outdir', help='Output directory')
args = parser.parse_args()

# if len(args.interferometers) == 1:
#     if ' ' in args.interferometers[0]:
#         args.interferometers = args.interferometers[0].split(" ")
# idx = args.idx
# injection_file = args.injection_file
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
elif glob('./*.lcf') > 0:
    cache_files = glob('./*.lcf')
    if args.channel_names is None:
        args.channel_names = [None]*len(cache_files)
    for cache_file, channel_name in zip(cache_files, args.channel_names):
        ifos.append(load_data_from_cache_file(
            cache_file, args.trigger_time, duration, args.psd_duration,
            channel_name))
elif glob('./*.gwf') > 0:
    # FIXME
    # for ifo in ifos:
    #     ifo.strain_data.roll_off = 0.0
    #     ifo_frame_files = [ff for ff in frames if ifo.name in ff]
    #     ifo_frame_file = [ff for ff in ifo_frame_files
    #                       if '{}_{}_'.format(ifo.name, frame_frame_start)
    #                       in ff][0]
    #     ifo.strain_data.set_from_frame_file(
    #         ifo_frame_file, sampling_frequency=sampling_frequency,
    #         duration=duration, frame_start=epoch,
    #         channel='{}:TBS_MDC'.format(ifo.name), buffer_time=0)
    #     if args.psd_duration > 0:
    #         if epoch - args.psd_duration > frame_frame_start:
    #             psd_frame_start = epoch - args.psd_duration
    #         else:
    #             psd_frame_start = epoch + duration
    #         ifo.power_spectral_density.set_from_frame_file(
    #             ifo_frame_file, psd_frame_start, args.psd_duration,
    #             fft_length=duration,
    #             sampling_frequency=sampling_frequency,
    #             roll_off=ifo.strain_data.roll_off,
    #             channel='{}:TBS_MDC'.format(ifo.name))
    raise Exception("This doesn't work.")
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
        likelihood=likelihood, priors=priors, sampler='pymultinest',
        label='{}_{}'.format(
            ''.join([ifo.name for ifo in ifos]), args.trigger_time),
        nlive=500, outdir=args.outdir,
        conversion_function=generate_all_bbh_parameters)
