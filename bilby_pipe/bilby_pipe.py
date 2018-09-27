#!/usr/bin/env python
"""
"""
import os
import json
import urllib2
import argparse


def get_output_directory(gracedb, label):
    outdir = 'PE_{}_{}'.format(gracedb, label)
    if os.path.isdir(outdir) is False:
        os.mkdir(outdir)
    return outdir


def set_up_argument_parsing():
    parser = argparse.ArgumentParser(
        usage='Query GraceDB and write results to json')
    parser.add_argument('--gracedb', type=str, required=True,
                        help='The gracedb event UID')
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
    from ligo.gracedb.rest import GraceDb

    # Initialise client and attempt to download
    client = GraceDb()
    try:
        candidate = client.event(gracedb)
    except urllib2.HTTPError:
        raise ValueError("No candidate found")

    outfilepath = os.path.join(outdir, '{}.json'.format(gracedb))

    # Write the candidate for future reference
    with open(outfilepath, 'w') as outfile:
            json.dump(candidate.json(), outfile, indent=2)

    return json


def main():
    args = set_up_argument_parsing()
    outdir = get_output_directory(args.gracedb, args.label)
    json = gracedb_to_json(args.gracedb, outdir)
