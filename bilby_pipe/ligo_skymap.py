#!/usr/bin/env python
"""
This a command line tool to prepare bilby results for use with ligo skymap
"""
import argparse
import os

import numpy as np
from h5py import File

from bilby.core.result import read_in_result

from .utils import logger


def get_args():
    parser = argparse.ArgumentParser(
        prog="bilby_pipe_to_ligo_skymap_samples", description=__doc__
    )
    parser.add_arg("input_file", type=str, help="The bilby file to convert")
    parser.add_arg("-o", "--out", type=str, help="The output hdf5 filename")
    parser.add_arg(
        "-n", "--nsamples", type=int, help="The maximum number of samples", default=None
    )
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    all_keys = [
        "ra",
        "dec",
        "luminosity_distance",
        "time",
        "mass_1",
        "mass_2",
        "spin1z",
        "spin2z",
    ]

    logger.info(f"Converting bilby result file {args.input_file}")
    result = read_in_result(args.input_file)
    posterior = result.posterior
    if "geocent_time" in posterior:
        posterior["time"] = posterior.pop("geocent_time")

    keys = [key for key in all_keys if key in posterior]
    samples = posterior[keys].to_records(index=False)

    if os.path.exists(result.outdir) is False:
        logger.info(
            f"The directory {result.outdir} is not accessible, falling back to"
            " the current working directory"
        )
        result.outdir = "."

    if args.out:
        output_file = args.out
    else:
        output_file = f"{result.outdir}/{result.label}_posterior_samples.hdf5"

    n = len(samples)
    if args.nsamples is not None and args.nsamples < n:
        samples = np.random.choice(samples, args.nsamples)
        n = len(samples)

    logger.info(f"Writing {n} ligo-skymap ready samples to {output_file}")
    with File(output_file, "w") as ff:
        ff.create_dataset(
            "posterior_samples",
            shape=samples.shape,
            dtype=samples.dtype,
            data=samples,
        )
