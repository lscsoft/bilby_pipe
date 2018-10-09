#!/usr/bin/env python
"""
"""
from __future__ import division, print_function
import numpy as np
import sys
import configargparse

import bilby
from bilby.core.utils import logger


parser = configargparse.ArgParser(ignore_unknown_config_file_keys=True)
parser.add('--ini', is_config_file=True, help='The ini-style config file')
parser.add('--gracedb', type=str, help='Gracedb UID', required=True)
parser.add('--detectors', nargs='+', default=['H1', 'L1'],
           help='The names of detectors to include {H1, L1}')
parser.add('--calibration', type=int, default=2,
           help='Which calibration to use')
parser.add('--duration', type=int, default=4,
           help='The duration of data around the event to use')
parser.add("--prior_file", default=None, help="prior file")
parser.add("--channel_names", default=None, nargs="*",
           help="Channel names to use, if not provided known "
           "channel names will be tested.")
parser.add('--psd_duration', default=500, type=int,
           help='Time used to generate the PSD, default is 500.')
parser.add('--dist-marg', dest='distance', action='store_true', default=False)
parser.add('--phase-marg', dest='phase', action='store_true', default=True)
parser.add('--time-marg', dest='time', action='store_true', default=True)
parser.add('--outdir', default='outdir', help='Output directory')
parser.add('--label', default='outdir', help='Output label')
parser.add('--sampler', default=None)
parser.add('--sampler-kwargs', default=None)
args = parser.parse_args()

logger.info(sys.argv)
logger.info('Command line arguments: {}'.format(args))

# Verify command line arguments
prior_file = args.prior_file
detectors = ' '.join(args.detectors).split(' ')  # Check to make sure is a list
duration = args.duration
sampling_frequency = 4096.

if args.sampler_kwargs:
    try:
        sampler_kwargs = eval(args.sampler_kwargs)
    except (NameError, TypeError) as e:
        raise ValueError(
            "Error {}. Unable to parse sampler_kwargs: {}"
            .format(e, args.sampler_kwargs))
else:
    sampler_kwargs = None

candidate, frame_caches = bilby.gw.utils.get_gracedb(
    args.gracedb, args.outdir, duration, args.calibration, detectors)
trigger_time = candidate['gpstime']

# Create the waveform_generator using a LAL BinaryBlackHole source function
par_cov = bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters
waveform_generator = bilby.gw.WaveformGenerator(
    sampling_frequency=sampling_frequency, duration=duration,
    frequency_domain_source_model=bilby.gw.source.lal_binary_black_hole,
    parameter_conversions=par_cov,
    waveform_arguments={
        'reference_frequency': 20., 'waveform_approximant': 'IMRPhenomPv2',
        'minimum_frequency': 20.})

# Set up interferometers.
ifos = bilby.gw.detector.InterferometerList([])
if frame_caches is not None:
    if args.channel_names is None:
        args.channel_names = [None] * len(frame_caches)
    for cache_file, channel_name in zip(frame_caches, args.channel_names):
        ifos.append(bilby.gw.detector.load_data_from_cache_file(
            cache_file, trigger_time, duration, args.psd_duration,
            channel_name))
else:
    raise Exception("Cannot find any data!")

# Generate a label for the output
label = '{}_{}_{}'.format(
    args.label, ''.join([ifo.name for ifo in ifos]), trigger_time)

# Set up prior
priors = bilby.gw.prior.BBHPriorSet(filename=prior_file)
priors['geocent_time'] = bilby.core.prior.Uniform(
    minimum=trigger_time - 0.1, maximum=trigger_time + 0.1,
    name='geocent_time', latex_label='$t_c$', unit='$s$')

likelihood = bilby.gw.likelihood.GravitationalWaveTransient(
    interferometers=ifos, waveform_generator=waveform_generator, prior=priors,
    phase_marginalization=args.phase, distance_marginalization=args.distance,
    time_marginalization=args.time)

sampling_seed = np.random.randint(1, 1e6)
np.random.seed(sampling_seed)
logger.info('Sampling seed is {}'.format(sampling_seed))

# Run sampler
result = bilby.run_sampler(
    likelihood=likelihood, priors=priors, sampler=args.sampler,
    label=label, outdir=args.outdir,
    conversion_function=bilby.gw.conversion.generate_all_bbh_parameters,
    **sampler_kwargs)
