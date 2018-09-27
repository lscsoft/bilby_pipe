#!/usr/bin/env python
"""
"""
import os
import json
import urllib3
import argparse
from .utils import logger
from . import utils


def get_output_directory(gracedb, label):
    outdir = 'PE_{}_{}'.format(gracedb, label)
    utils.check_directory_exists_and_if_not_mkdir(outdir)
    return outdir


def set_up_argument_parsing():
    parser = argparse.ArgumentParser(
        usage='Query GraceDB and write results to json')
    parser.add_argument('--gracedb', type=str, required=True,
                        help='The gracedb event UID')
    parser.add_argument('--detectors', nargs='+', default=['H1', 'L1'],
                        help='The detector names, {H1, L1}')
    parser.add_argument('--calibration', type=int, default=2,
                        help='Which calibration to use')
    parser.add_argument('--duration', type=int, default=4,
                        help='The duration of data about the event to use')
    parser.add_argument('--label', type=str, required=True,
                        help='A unique label for the query')
    return parser.parse_args()


def gracedb_to_json(gracedb, outdir=None):
    """ Script to download a GraceDB candidate

    Parameters
    ----------
    gracedb: str
        The UID of the GraceDB candidate
    outdir: str, optional
        If given, a string identfying the location in which to store the json
    """
    logger.info(
        'Starting routine to download GraceDb candidate {}'.format(gracedb))
    from ligo.gracedb.rest import GraceDb

    logger.info('Initialise client and attempt to download')
    client = GraceDb()
    try:
        candidate = client.event(gracedb)
        logger.info('Successfully downloaded candidate')
    except urllib3.HTTPError:
        raise ValueError("No candidate found")


    json_output = candidate.json()

    if outdir is not None:
        outfilepath = os.path.join(outdir, '{}.json'.format(gracedb))
        logger.info('Writing candidate to {}'.format(outfilepath))
        with open(outfilepath, 'w') as outfile:
                json.dump(json_output, outfile, indent=2)

    return json_output


def gw_data_find(observatory, gps_start_time, duration, calibration,
                 outdir='.'):
    """ Builds a gw_data_find call and process output

    Parameters
    ----------
    observatory: str, {H1, L1}
        Observatory description
    gps_start_time: float
        The start time in gps to look for data
    duration: int
        The duration (integer) in s
    calibrartion: int {1, 2}
        Use C01 or C02 calibration
    outdir: string
        A path to the directory where output is stored

    Returns
    -------
    output_cache_file: str
        Path to the output cache file

    """
    logger.info('Building gw_data_find command line')

    observatory_lookup = dict(H1='H', L1='L')
    observatory_code = observatory_lookup[observatory]

    dtype = '{}_HOFT_C0{}'.format(observatory, calibration)
    logger.info('Using LDRDataFind query type {}'.format(dtype))

    cache_file = '{}-{}_CACHE-{}-{}.lcf'.format(
        observatory, dtype, gps_start_time, duration)
    output_cache_file = os.path.join(outdir, cache_file)

    gps_end_time = gps_start_time + duration

    cl_list = ['gw_data_find']
    cl_list.append('--observatory {}'.format(observatory_code))
    cl_list.append('--gps-start-time {}'.format(gps_start_time))
    cl_list.append('--gps-end-time {}'.format(gps_end_time))
    cl_list.append('--type {}'.format(dtype))
    cl_list.append('--output {}'.format(output_cache_file))
    cl_list.append('--url-type file')
    cl_list.append('--lal-cache')
    cl = ' '.join(cl_list)
    utils.run_commandline(cl)
    return output_cache_file


def main():
    args = set_up_argument_parsing()
    outdir = get_output_directory(args.gracedb, args.label)
    candidate = gracedb_to_json(args.gracedb, outdir)
    event_time = candidate['gpstime']
    gps_start_time = event_time - args.duration
    cache_files = []
    for det in args.detectors:
        output_cache_file = gw_data_find(
            det, gps_start_time, args.duration, args.calibration,
            outdir=outdir)
        cache_files.append(output_cache_file)
