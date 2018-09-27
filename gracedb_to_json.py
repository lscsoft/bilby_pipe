#!/usr/bin/env python
"""
A tool for accessing the GraceDb rest API to store a candidate properties in a
json file
"""
import os
import json
import urllib2
import argparse
from ligo.gracedb.rest import GraceDb

# Set up argument parsing
parser = argparse.ArgumentParser(
    usage='Query GraceDB and write results to json')
parser.add_argument('--gracedb', type=str, required=True,
                    help='The gracedb event UID')
parser.add_argument('--label', type=str, required=True,
                    help='A unique label for the query')
args = parser.parse_args()

# Initialise client and attempt to download
client = GraceDb()
try:
    candidate = client.event(args.gracedb)
except urllib2.HTTPError:
    raise ValueError("No candidate found")

# Define the output directory and path. Create the directory if needed.
outdir = 'PE_{}_{}'.format(args.gracedb, args.label)
if os.path.isdir(outdir) is False:
    os.mkdir(outdir)
outfilepath = os.path.join(outdir, '{}.json'.format(args.gracedb))

# Write the candidate to the json output
with open(outfilepath, 'w') as outfile:
        json.dump(candidate.json(), outfile, indent=2)
