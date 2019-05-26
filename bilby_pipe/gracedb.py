""" Tools for using gracedb events accessed through bilby_pipe_gracedb """
import argparse
import json
import os
import subprocess
import shutil
import time

import bilby
import bilby_pipe
from .utils import logger


def x509userproxy(args):
    cert_alias = "X509_USER_PROXY"
    try:
        cert_path = os.environ[cert_alias]
        new_cert_path = os.path.join(args.outdir, "." + os.path.basename(cert_path))
        shutil.copyfile(cert_path, new_cert_path)
        x509userproxy = new_cert_path
    except FileNotFoundError:
        logger.warning(
            "Environment variable X509_USER_PROXY does not point to a"
            " file. Try running `$ ligo-proxy-init albert.einstein`"
        )
    except KeyError:
        logger.warning(
            "Environment variable X509_USER_PROXY not set"
            " Try running `$ ligo-proxy-init albert.einstein`"
        )
        x509userproxy = None
    return x509userproxy


def get_gracedb(args):
    bilby_pipe.utils.test_connection()
    candidate = bilby.gw.utils.gracedb_to_json(
        gracedb=args.gracedb,
        outdir=args.outdir,
        cred=x509userproxy(args),
        service_url=args.gracedb_url,
    )

    return candidate


def coinc(args):
    try:
        with open(args.coinc, "r") as file:
            candidate = json.load(file)
    except IOError:
        print("Unable to load event contents of json file")

    return candidate


def create_config_file(args, candidate):
    chirp_mass = candidate["extra_attributes"]["CoincInspiral"]["mchirp"]
    trigger_time = candidate["gpstime"]
    singleinspiraltable = candidate["extra_attributes"]["SingleInspiral"]

    ifos = [sngl["ifo"] for sngl in singleinspiraltable]
    channels = [sngl["channel"] for sngl in singleinspiraltable]
    ifo_channel = zip(ifos, channels)
    channel_dict = {}
    for ifo, channel in ifo_channel:
        channel_dict[ifo] = channel

    if args.gracedb is None:
        args.gracedb = candidate["graceid"]

    config_dict = dict(
        label=args.gracedb,
        outdir=args.outdir,
        accounting="ligo.dev.o3.cbc.pe.lalinference",
        maximum_frequency=1024,
        minimum_frequency=20,
        sampling_frequency=4096,
        reference_frequency=20,
        trigger_time=trigger_time,
        detectors="[H1, L1, V1]",
        channel_dict=channel_dict,
        deltaT=0.1,
        prior_file=determine_prior_file_from_parameters(chirp_mass),
        duration=8,
        sampler="dynesty",
        sampler_kwargs="{nlive: 1000, walks: 100, n_check_point: 5000}",
        create_plots=True,
        time_marginalization=True,
        distance_marginalization=True,
        phase_marginalization=True,
    )
    filename = write_config_file(config_dict)

    return filename


def write_config_file(config_dict):
    if None in config_dict.values():
        raise ValueError("config-dict is not complete")
    filename = "{}.ini".format(config_dict["label"])
    with open(filename, "w+") as file:
        for key, val in config_dict.items():
            print("{}={}".format(key, val), file=file)

    return filename


def determine_prior_file_from_parameters(chirp_mass):
    """ 
    Determine appropriate prior from chirp mass

    Parameters 
    ----------
    chirp_mass: float
        The chirp mass of the source (in solar masses)

    Returns
    -------
    prior: str
        A string repesentation of the appropriate prior to use
    """

    if chirp_mass > 40:
        prior = "high_mass"
    elif chirp_mass > 13.53:
        prior = "4s"
    elif chirp_mass > 8.73:
        prior = "8s"
    elif chirp_mass > 5.66:
        prior = "16s"
    elif chirp_mass > 3.68:
        prior = "32s"
    elif chirp_mass > 2.39:
        prior = "64s"
    else:
        prior = "128s"

    return prior


def run_command_line(arguments):
    print("\nRunning command $ {}\n".format(" ".join(arguments)))
    subprocess.call(arguments)


def main():
    parser = argparse.ArgumentParser(prog="bilby_pipe gracedb access", usage="")
    group1 = parser.add_mutually_exclusive_group(required=True)
    group1.add_argument("--gracedb", type=str, help="GraceDB event id")
    group1.add_argument("--coinc", type=str, help="Path to coinc_file")
    group2 = parser.add_mutually_exclusive_group(required=False)
    group2.add_argument("--local", action="store_true", help="Run the job locally")
    group2.add_argument("--submit", action="store_true", help="Submit the job")
    parser.add_argument("--outdir", type=str, help="Output directory")
    parser.add_argument("--gracedb-url", type=str, help="GraceDB service url")

    args = parser.parse_args()

    if args.gracedb_url is None:
        args.gracedb_url = "https://gracedb.ligo.org/api/"

    if args.coinc:
        candidate = coinc(args)
        gracedb = candidate["graceid"]
        if args.outdir is None:
            args.outdir = "outdir_{}".format(gracedb)
        if not os.path.exists(args.outdir):
            os.mkdir(args.outdir)

    if args.gracedb:
        if args.outdir is None:
            args.outdir = "outdir_{}".format(args.gracedb)
        if not os.path.exists(args.outdir):
            os.mkdir(args.outdir)
        candidate = get_gracedb(args)

    filename = create_config_file(args, candidate)

    arguments = ["bilby_pipe", filename]
    if args.local:
        arguments.append("--local")
    if args.submit:
        arguments.append("--submit")
    run_command_line(arguments)
