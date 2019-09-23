""" Tool for running online bilby PE using GraceDB events

The functionality of much of these utility assumes the user is running on the
CIT cluster, e.g. the ROQ and calibration directories are in there usual place
"""
import argparse
import json
import os
import shutil

import numpy as np

import bilby
import bilby_pipe
from .utils import (
    BilbyPipeError,
    check_directory_exists_and_if_not_mkdir,
    logger,
    DEFAULT_DISTANCE_LOOKUPS,
    write_config_file,
    run_command_line,
)


# Default channels from: https://wiki.ligo.org/LSC/JRPComm/ObsRun3
CHANNEL_DICTS = dict(
    online=dict(
        H1="GDS-CALIB_STRAIN_CLEAN", L1="GDS-CALIB_STRAIN_CLEAN", V1="Hrec_hoft_16384Hz"
    ),
    o2replay=dict(
        H1="GDS-CALIB_STRAIN_O2Replay",
        L1="GDS-CALIB_STRAIN_O2Replay",
        V1="Hrec_hoft_16384Hz_O2Replay",
    ),
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


def calibration_lookup(trigger_time, detector):
    """ Lookup function for the relevant calibration file

    Assumes that it is running on CIT where the calibration files are stored
    under /home/cbc/pe/O3/calibrationenvelopes

    Parameters
    ----------
    trigger_time: float
        The trigger time of interest
    detector: str [H1, L1, V1]
        Detector string

    Returns
    -------
    filepath: str
        The path to the relevant calibration envelope file. If no calibration
        file can be determined, None is returned.

    """
    base = "/home/cbc/pe/O3/calibrationenvelopes"
    CALENVS_LOOKUP = dict(
        H1=os.path.join(base, "LIGO_Hanford/H_CalEnvs.txt"),
        L1=os.path.join(base, "LIGO_Livingston/L_CalEnvs.txt"),
        V1=os.path.join(base, "Virgo/V_CalEnvs.txt"),
    )

    if os.path.isdir(base) is False:
        raise BilbyPipeError("Unable to read from calibration folder {}".format(base))

    calenv = CALENVS_LOOKUP[detector]
    times = []
    files = []
    with open(calenv, "r") as f:
        for line in f:
            time, filename = line.rstrip("\n").split(" ")
            times.append(float(time))
            files.append(filename)

    if trigger_time < times[0]:
        raise BilbyPipeError(
            "Requested trigger time prior to earliest calibration file"
        )

    for i, time in enumerate(times):
        if trigger_time > time:
            directory = os.path.dirname(calenv)
            calib_file = "{}/{}".format(directory, files[i])
            return os.path.abspath(calib_file)


def calibration_dict_lookup(trigger_time, detectors):
    """ Dictionary lookup function for the relevant calibration files

    Parameters
    ----------
    trigger_time: float
        The trigger time of interest
    detectors: list
        List of detector string

    Returns
    -------
    calibration_model, calibration_dict: str, dict
        Calibration model string and dictionary of paths to the relevant
        calibration envelope file.
    """

    try:
        calibration_dict = {
            det: calibration_lookup(trigger_time, det) for det in detectors
        }
        return "CubicSpline", calibration_dict
    except BilbyPipeError:
        return None, None


def read_candidate(candidate):
    """ Read a gracedb candidate json dictionary """
    try:
        chirp_mass = candidate["extra_attributes"]["CoincInspiral"]["mchirp"]
    except KeyError:
        raise BilbyPipeError(
            "Unable to determine chirp mass for {} from GraceDB".format(
                candidate["graceid"]
            )
        )
    superevent = candidate["superevent"]
    trigger_time = candidate["gpstime"]
    singleinspiraltable = candidate["extra_attributes"]["SingleInspiral"]

    ifos = [sngl["ifo"] for sngl in singleinspiraltable]
    return chirp_mass, superevent, trigger_time, ifos


def prior_lookup(duration, scale_factor, outdir):
    """ Lookup the appropriate prior and apply rescaling factors

    Parameters
    ----------
    duration: float
        Inferred duration of the signal
    scale_factor: float
    outdir: str
        Output directory

    Returns
    -------
    prior_file, roq_folder: str
        Path to the prior file to use usually written to the outdir, and the
        roq folder
    duration, minimum_frequency, maximum_frequency: int
        The duration, minimum and maximum frequency to use (rescaled if needed)

    """

    roq_folder = "/home/cbc/ROQ_data/IMRPhenomPv2/{}s".format(duration)
    if os.path.isdir(roq_folder) is False:
        logger.warning("Requested ROQ folder does not exist")
        return "{}s".format(duration), None, duration, 20, 1024

    roq_params = np.genfromtxt(os.path.join(roq_folder, "params.dat"), names=True)

    prior_file = generate_prior_from_template(
        duration=duration,
        roq_params=roq_params,
        scale_factor=scale_factor,
        outdir=outdir,
    )

    minimum_frequency = roq_params["flow"] * scale_factor
    maximum_frequency = roq_params["fhigh"] * scale_factor
    duration /= scale_factor
    return prior_file, roq_folder, duration, minimum_frequency, maximum_frequency


def create_config_file(
    candidate, gracedb, outdir, channel_dict, sampler_kwargs, webdir, roq=True
):
    """ Creates ini file from defaults and candidate contents

    Parameters
    ----------
    candidate:
        Contains contents of GraceDB event
    gracedb: str
        GraceDB id of event
    outdir: str
        Output directory where the ini file and all output is written
    channel_dict: dict
        Dictionary of channel names
    sampler_kwargs: str
        Set of sampler arguments, or option for set of sampler arguments
    webdir: str
        Directory to store summary pages
    roq: bool
        If True, use the default ROQ settings if required

    Returns
    -------
    filename: str
        Generated ini filename

    """

    chirp_mass, superevent, trigger_time, ifos = read_candidate(candidate)

    duration, scale_factor = determine_duration_and_scale_factor_from_parameters(
        chirp_mass
    )

    distance_marginalization_lookup_table = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "data_files",
        "{}s_distance_marginalization_lookup.npz".format(duration),
    )

    prior_file, roq_folder, duration, minimum_frequency, maximum_frequency = prior_lookup(
        duration, scale_factor, outdir
    )
    calibration_model, calib_dict = calibration_dict_lookup(trigger_time, ifos)

    config_dict = dict(
        label=gracedb,
        outdir=outdir,
        accounting="ligo.dev.o3.cbc.pe.lalinference",
        maximum_frequency=maximum_frequency,
        minimum_frequency=minimum_frequency,
        sampling_frequency=16384,
        reference_frequency=100,
        trigger_time=trigger_time,
        detectors=ifos,
        channel_dict=channel_dict,
        deltaT=0.2,
        prior_file=prior_file,
        duration=duration,
        roq_scale_factor=scale_factor,
        sampler="dynesty",
        sampler_kwargs=sampler_kwargs,
        webdir=webdir,
        create_plots=True,
        local_generation=True,
        local_plot=True,
        transfer_files=False,
        time_marginalization=True,
        distance_marginalization=True,
        phase_marginalization=True,
        distance_marginalization_lookup_table=distance_marginalization_lookup_table,
        n_parallel=4,
        create_summary=True,
        calibration_model=calibration_model,
        spline_calibration_envelope_dict=calib_dict,
        spline_calibration_nodes=10,
    )

    if roq and config_dict["duration"] > 4 and roq_folder is not None:
        config_dict["likelihood-type"] = "ROQGravitationalWaveTransient"
        config_dict["roq-folder"] = roq_folder

    comment = "# Configuration ini file generated from GraceDB superevent {}".format(
        superevent
    )
    filename = "{}/bilby_config.ini".format(outdir)
    write_config_file(config_dict, filename, comment, remove_none=True)

    return filename


def determine_duration_and_scale_factor_from_parameters(chirp_mass):
    """ Determine appropriate duration and roq scale factor from chirp mass

    Parameters
    ----------
    chirp_mass: float
        The chirp mass of the source (in solar masses)

    Returns
    -------
    duration: int
    roq_scale_factor: float
    """
    roq_scale_factor = 1
    if chirp_mass > 90:
        duration = 4
        roq_scale_factor = 4
    elif chirp_mass > 35:
        duration = 4
        roq_scale_factor = 2
    elif chirp_mass > 13.53:
        duration = 4
    elif chirp_mass > 8.73:
        duration = 8
    elif chirp_mass > 5.66:
        duration = 16
    elif chirp_mass > 3.68:
        duration = 32
    elif chirp_mass > 2.39:
        duration = 64
    elif chirp_mass > 1.43:
        duration = 128
    elif chirp_mass > 1.3:
        duration = 128
        roq_scale_factor = 1 / 1.6
    else:
        duration = 128
        roq_scale_factor = 1 / 2

    return duration, round(1 / roq_scale_factor, 1)


def generate_prior_from_template(
    duration, roq_params, scale_factor=1, outdir=".", template=None
):
    """ Generate a prior file from a template and write it to file

    Parameters
    ----------
    duration: float
        The segment duration
    roq_params: dict
        Dictionary of the ROQ params.dat file
    scale_factor: float
        Rescaling factor
    outdir: str
        Path to the outdir (the prior is written to outdir/online.prior)
    template: str
        Alternative template file to use, otherwise the
        data_files/roq.prior.template file is used
    """
    distance_bounds = DEFAULT_DISTANCE_LOOKUPS[str(duration) + "s"]
    mc_min = roq_params["chirpmassmin"] / scale_factor
    mc_max = roq_params["chirpmassmax"] / scale_factor

    if template is None:
        template = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "data_files/roq.prior.template"
        )

    with open(template, "r") as old_prior:
        prior_string = old_prior.read().format(
            mc_min=mc_min,
            mc_max=mc_max,
            d_min=distance_bounds[0],
            d_max=distance_bounds[1],
        )
    prior_file = os.path.join(outdir, "online.prior")
    with open(prior_file, "w") as new_prior:
        new_prior.write(prior_string)
    return prior_file


def create_parser():
    parser = argparse.ArgumentParser(prog="bilby_pipe gracedb access", usage=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    group1 = parser.add_mutually_exclusive_group(required=True)
    group1.add_argument("--gracedb", type=str, help="GraceDB event id")
    group1.add_argument("--json", type=str, help="Path to json gracedb file")
    parser.add_argument(
        "--outdir",
        type=str,
        help="Output directory where the ini file and all output is written.",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["ini", "full", "full-local", "full-submit"],
        help=(
            "Flag to create ini, generate directories and/or submit. \n"
            " ini         : generates ini file \n"
            " full        : generates ini and dag submission files (default) \n"
            " full-local  : generates ini and dag submission files and run locally \n"
            " full-submit : generates ini and dag submission files and submits to condor \n"
        ),
        default="full",
    )
    parser.add_argument(
        "--gracedb-url",
        type=str,
        help=(
            "GraceDB service url. \n"
            " Main page  : https://gracedb.ligo.org/api/ (default) \n"
            " Playground : https://gracedb-playground.ligo.org/api/ \n"
        ),
        default="https://gracedb.ligo.org/api/",
    )
    parser.add_argument(
        "--channel-dict",
        type=str,
        default="online",
        choices=list(CHANNEL_DICTS.keys()),
        help=(
            "Channel dictionary. \n"
            " online   : use for main GraceDB page events (default)\n"
            " o2replay : use for playground GraceDB page events"
        ),
    )
    parser.add_argument(
        "--sampler-kwargs",
        type=str,
        default="Default",
        help=(
            "Dictionary of sampler-kwargs to pass in, e.g., {nlive: 1000} OR "
            "pass pre-defined set of sampler-kwargs {Default, FastTest}"
        ),
    )
    parser.add_argument(
        "--webdir",
        type=str,
        default=None,
        help=(
            "Directory to store summary pages. \n"
            " If not given, defaults to outdir/results_page"
        ),
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

    if args.webdir is not None:
        webdir = args.webdir
    else:
        webdir = os.path.join(outdir, "results_page")

    sampler_kwargs = args.sampler_kwargs
    channel_dict = CHANNEL_DICTS[args.channel_dict.lower()]
    filename = create_config_file(
        candidate, gracedb, outdir, channel_dict, sampler_kwargs, webdir
    )

    if args.output == "ini":
        logger.info(
            "Generating ini with default settings. Run using the command: \n"
            " $ bilby_pipe {}".format(filename)
        )
    else:
        arguments = ["bilby_pipe", filename]
        if args.output == "full":
            logger.info("Generating dag submissions files")
        if args.output == "full-local":
            logger.info("Generating dag submission files, running locally")
            arguments.append("--local")
        if args.output == "full-submit":
            logger.info("Generating dag submissions files, submitting to condor")
            arguments.append("--submit")
        run_command_line(arguments)
