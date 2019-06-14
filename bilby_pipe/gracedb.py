""" Tools for using gracedb events accessed through bilby_pipe_gracedb """
import argparse
import json
import os
import shutil

import bilby
import bilby_pipe
from .utils import (
    BilbyPipeError,
    check_directory_exists_and_if_not_mkdir,
    logger,
    duration_lookups,
    maximum_frequency_lookups,
    write_config_file,
    run_command_line,
)


def x509userproxy(outdir):
    """ Copies X509_USER_PROXY certificate from user's os.environ and
    places it inside the outdir, if the X509_USER_PROXY exists.

    Parameters
    ----------
    outdir: str
        Output directory where X509_USER_PROXY certificate is copied to.

    Returns
    -------
    x509userproxy: str, None
        New path to X509_USER_PROXY certification file

        None if X509_USER_PROXY certificate does not exist, or if
        the X509_USER_PROXY cannot be copied.
    """
    x509userproxy = None
    cert_alias = "X509_USER_PROXY"
    print(os.environ)
    try:
        cert_path = os.environ[cert_alias]
        new_cert_path = os.path.join(outdir, "." + os.path.basename(cert_path))
        shutil.copyfile(src=cert_path, dst=new_cert_path)
        x509userproxy = new_cert_path
    except FileNotFoundError as e:
        logger.warning(
            "Environment variable X509_USER_PROXY does not point to a file. "
            "Error while copying file: {}. "
            "Try running `$ ligo-proxy-init albert.einstein`".format(e)
        )
    except KeyError:
        logger.warning(
            "Environment variable X509_USER_PROXY not set"
            " Try running `$ ligo-proxy-init albert.einstein`"
        )
    return x509userproxy


def read_from_gracedb(gracedb, gracedb_url, outdir):
    """
    Read GraceDB events from GraceDB

    Parameters
    ----------
    gracedb: str
        GraceDB id of event
    gracedb_url: str
        Service url for GraceDB events
        GraceDB 'https://gracedb.ligo.org/api/' (default)
        GraceDB-playground 'https://gracedb-playground.ligo.org/api/'
    outdir: str
        Output directory

    Returns
    -------
    candidate:
        Contains contents of GraceDB event from GraceDB, json format

    """

    bilby_pipe.utils.test_connection()
    candidate = bilby.gw.utils.gracedb_to_json(
        gracedb=gracedb,
        outdir=outdir,
        cred=x509userproxy(outdir),
        service_url=gracedb_url,
    )
    return candidate


def read_from_json(json_file):
    """ Read GraceDB events from json file

    Parameters
    ----------
    json_file: str
        Filename of json json file output

    Returns
    -------
    candidate: dict
        Contains contents of GraceDB event from json, json format

    """

    if os.path.isfile(json_file) is False:
        raise FileNotFoundError("File {} not found".format(json_file))

    try:
        with open(json_file, "r") as file:
            candidate = json.load(file)
    except IOError:
        logger.warning("Unable to load event contents of json file")

    return candidate


def create_config_file(candidate, gracedb, outdir, roq=True):
    """ Creates ini file from defaults and candidate contents

    Parameters
    ----------
    candidate:
        Contains contents of GraceDB event
    gracedb: str
        GraceDB id of event
    outdir: str
        Output directory where the ini file and all output is written
    roq: bool
        If True, use the default ROQ settings if required

    Returns
    -------
    filename: str
        Generated ini filename

    """

    try:
        chirp_mass = candidate["extra_attributes"]["CoincInspiral"]["mchirp"]
    except KeyError:
        raise BilbyPipeError(
            "Unable to determine chirp mass for {} from GraceDB".format(gracedb)
        )
    trigger_time = candidate["gpstime"]
    singleinspiraltable = candidate["extra_attributes"]["SingleInspiral"]

    ifos = [sngl["ifo"] for sngl in singleinspiraltable]

    # Default channels set from: https://wiki.ligo.org/LSC/JRPComm/ObsRun3
    DEFAULT_CHANNEL_DICT = {
        "H1: GDS-CALIB_STRAIN_CLEAN",
        "L1: GDS-CALIB_STRAIN_CLEAN",
        "V1: Hrec_hoft_16384Hz",
    }

    prior = determine_prior_file_from_parameters(chirp_mass)

    config_dict = dict(
        label=gracedb,
        outdir=outdir,
        accounting="ligo.dev.o3.cbc.pe.lalinference",
        maximum_frequency=maximum_frequency_lookups[prior],
        minimum_frequency=20,
        sampling_frequency=maximum_frequency_lookups[prior] * 4,
        reference_frequency=20,
        trigger_time=trigger_time,
        detectors=ifos,
        channel_dict=DEFAULT_CHANNEL_DICT,
        deltaT=0.2,
        prior_file=prior,
        duration=duration_lookups[prior],
        sampler="dynesty",
        sampler_kwargs="{nlive: 1000, walks: 100, check_point_plot=True, n_check_point: 5000}",
        create_plots=True,
        local_generation=True,
        local_plot=True,
        transfer_files=False,
        time_marginalization=True,
        distance_marginalization=True,
        phase_marginalization=True,
        n_parallel=4,
        create_summary=True,
    )

    if roq and config_dict["duration"] > 4:
        config_dict["likelihood-type"] = "ROQGravitationalWaveTransient"
        config_dict["roq-folder"] = "/home/cbc/ROQ_data/IMRPhenomPv2/{}".format(prior)

    filename = "{}/{}.ini".format(outdir, config_dict["label"])
    write_config_file(config_dict, filename)

    return filename


def determine_prior_file_from_parameters(chirp_mass):
    """ Determine appropriate prior from chirp mass

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


def create_parser():
    parser = argparse.ArgumentParser(prog="bilby_pipe gracedb access", usage="")
    group1 = parser.add_mutually_exclusive_group(required=True)
    group1.add_argument("--gracedb", type=str, help="GraceDB event id")
    group1.add_argument("--json", type=str, help="Path to json gracedb file")
    group2 = parser.add_mutually_exclusive_group(required=False)
    group2.add_argument("--local", action="store_true", help="Run the job locally")
    group2.add_argument("--submit", action="store_true", help="Submit the job")
    parser.add_argument(
        "--outdir",
        type=str,
        help="Output directory where the ini file and all output is written",
    )
    parser.add_argument(
        "--gracedb-url",
        type=str,
        help="GraceDB service url",
        default="https://gracedb.ligo.org/api/",
    )
    return parser


def main(args=None):

    if args is None:
        args = create_parser().parse_args()

    if args.outdir:
        outdir = args.outdir

    if args.json:
        json = args.json
        candidate = read_from_json(json)
        gracedb = candidate["graceid"]
        if args.outdir is None:
            outdir = "outdir_{}".format(gracedb)
        check_directory_exists_and_if_not_mkdir(outdir)

    if args.gracedb:
        gracedb = args.gracedb
        gracedb_url = args.gracedb_url
        if args.outdir is None:
            outdir = "outdir_{}".format(gracedb)
        check_directory_exists_and_if_not_mkdir(outdir)
        candidate = read_from_gracedb(gracedb, gracedb_url, outdir)

    filename = create_config_file(candidate, gracedb, outdir)

    arguments = ["bilby_pipe", filename]
    if args.local:
        arguments.append("--local")
    if args.submit:
        arguments.append("--submit")
    run_command_line(arguments)
