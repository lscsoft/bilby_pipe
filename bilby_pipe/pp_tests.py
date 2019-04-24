#!/usr/bin/env python
""" Tools to analyse a set of runs for parameter-parameter plots """

import argparse
import glob
import json
import os

from bilby.core.result import read_in_result, make_pp_plot
import matplotlib.pyplot as plt
import numpy as np
import tqdm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", help="Path to the result files")
    parser.add_argument(
        "-n", type=int, help="Number of samples to truncate to", default=None
    )
    args, _ = parser.parse_known_args()

    results_files = glob.glob(os.path.join(args.directory + "*result*"))
    if len(results_files) == 0:
        raise ValueError("No results found in path {}".format(args.directory))

    if args.n is not None:
        results_files = results_files[: args.n]

    print("Reading in results ...")
    results = []
    for f in tqdm.tqdm(results_files):
        try:
            results.append(read_in_result(f))
        except json.decoder.JSONDecodeError:
            pass
    print("Read in {} results from directory {}".format(len(results), args.directory))

    print("Checking if results are complete")
    results_u = []
    for r in results:
        try:
            r.posterior
            results_u.append(r)
        except ValueError:
            pass
    if len(results_u) < len(results):
        print("Results incomplete, truncating to {}".format(len(results_u)))
        results = results_u
    else:
        print("Results complete")

    r0 = results[0]
    sampler = r0.sampler
    nlive = r0.sampler_kwargs["nlive"]
    walks = r0.sampler_kwargs["walks"]
    label = "{}/{}_nlive{}_walks{}".format(args.directory, sampler, nlive, walks)

    print("Create the PP plot")
    keys = r0.priors.keys()
    print("Parameters = {}".format(keys))
    make_pp_plot(results, filename="{}_pp.png".format(label), keys=keys)

    print("Create sampling-time histogram")
    stimes = [r.sampling_time for r in results]
    fig, ax = plt.subplots()
    ax.hist(np.array(stimes) / 3600, bins=50)
    ax.set_xlabel("Sampling time [hr]")
    fig.tight_layout()
    fig.savefig("{}_sampling_times.png".format(label))

    print("Create optimal SNR plot")
    fig, ax = plt.subplots()
    snrs = []
    for det in ["H1", "L1"]:
        snrs.append(
            [
                r.meta_data["likelihood"]["interferometers"][det]["optimal_SNR"]
                for r in results
            ]
        )

    network_snr = np.sqrt(np.sum(np.array(snrs) ** 2, axis=0))
    ax.hist(network_snr, bins=50, label=det)
    ax.set_xlabel("Network optimal SNR")
    fig.tight_layout()
    fig.savefig("{}_optimal_SNR.png".format(label))
