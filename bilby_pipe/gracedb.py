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

from . import parser
from .utils import (
    DEFAULT_DISTANCE_LOOKUPS,
    BilbyPipeError,
    check_directory_exists_and_if_not_mkdir,
    logger,
    next_power_of_2,
    run_command_line,
    tcolors,
    test_connection,
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

CBC_PIPELINES = ["gstlal", "pycbc", "mbtaonline", "spiir"]
BURST_PIPELINES = ["cwb"]


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

    test_connection()
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
    times = list()
    files = dict()
    with open(calenv, "r") as f:
        for line in f:
            time, filename = line.rstrip("\n").rstrip().split(" ")
            times.append(float(time))
            files[float(time)] = filename
    times = sorted(times)

    if trigger_time < times[0]:
        raise BilbyPipeError(
            "Requested trigger time prior to earliest calibration file"
        )

    for time in times:
        if trigger_time > time:
            directory = os.path.dirname(calenv)
            calib_file = "{}/{}".format(directory, files[time])
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
    if "extra_attributes" not in candidate:
        raise BilbyPipeError(
            "Cannot parse event dictionary, not 'extra_attributes' present."
        )
    elif "CoincInspiral" in candidate["extra_attributes"]:
        return _read_cbc_candidate(candidate)
    elif "MultiBurst" in candidate["extra_attributes"]:
        return _read_burst_candidate(candidate)


def _read_cbc_candidate(candidate):
    if "mchirp" not in candidate["extra_attributes"]["CoincInspiral"]:
        raise BilbyPipeError(
            "Unable to determine chirp mass for {} from GraceDB".format(
                candidate["graceid"]
            )
        )
    chirp_mass = candidate["extra_attributes"]["CoincInspiral"]["mchirp"]
    superevent = candidate["superevent"]
    trigger_time = candidate["gpstime"]
    ifos = [sngl["ifo"] for sngl in candidate["extra_attributes"]["SingleInspiral"]]
    return chirp_mass, superevent, trigger_time, ifos


def _read_burst_candidate(candidate):
    central_frequency = candidate["extra_attributes"]["MultiBurst"]["central_freq"]
    superevent = candidate["superevent"]
    trigger_time = candidate["gpstime"]
    ifos = candidate["extra_attributes"]["MultiBurst"]["ifos"].split()
    return central_frequency, superevent, trigger_time, ifos


def prior_lookup(duration, scale_factor, outdir, template=None):
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
        template=template,
    )

    minimum_frequency = roq_params["flow"] * scale_factor
    maximum_frequency = roq_params["fhigh"] * scale_factor
    duration /= scale_factor
    return prior_file, roq_folder, duration, minimum_frequency, maximum_frequency


def create_config_file(
    candidate,
    gracedb,
    outdir,
    channel_dict,
    sampler_kwargs,
    webdir,
    convert_to_flat_in_component_mass=False,
    roq=True,
    search_type="cbc",
    online=False,
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
    convert_to_flat_in_component_mass: bool
        If True, will convert to a flat in component mass prior after running
    search_type: str
        What kind of search identified the trigger, options are "cbc" and "burst"
    online: bool
        Whether this is running online. This disables the pesummary ligo-skymap

    Returns
    -------
    filename: str
        Generated ini filename

    """

    if search_type == "cbc":
        chirp_mass, superevent, trigger_time, ifos = _read_cbc_candidate(candidate)

        duration, scale_factor = determine_duration_and_scale_factor_from_parameters(
            chirp_mass
        )

        distance_marginalization_lookup_table = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "data_files",
            "{}s_distance_marginalization_lookup.npz".format(duration),
        )

        if sampler_kwargs == "FastTest":
            template = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "data_files/fast.prior.template",
            )
        else:
            template = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "data_files/roq.prior.template",
            )

        (
            prior_file,
            roq_folder,
            duration,
            minimum_frequency,
            maximum_frequency,
        ) = prior_lookup(
            duration=duration,
            scale_factor=scale_factor,
            outdir=outdir,
            template=template,
        )
        calibration_model, calib_dict = calibration_dict_lookup(trigger_time, ifos)

        if calibration_model is None:
            spline_calibration_nodes = 0
        elif sampler_kwargs == "FastTest":
            spline_calibration_nodes = 4
        else:
            spline_calibration_nodes = 10

        extra_config_arguments = dict(
            reference_frequency=100,
            time_marginalization=True,
            distance_marginalization=True,
            phase_marginalization=True,
            distance_marginalization_lookup_table=distance_marginalization_lookup_table,
            roq_scale_factor=scale_factor,
            convert_to_flat_in_component_mass=convert_to_flat_in_component_mass,
            create_plots=True,
            calibration_model=calibration_model,
            spline_calibration_envelope_dict=calib_dict,
            spline_calibration_nodes=spline_calibration_nodes,
        )
        if roq and duration > 4 and roq_folder is not None:
            extra_config_arguments["likelihood-type"] = "ROQGravitationalWaveTransient"
            extra_config_arguments["roq-folder"] = roq_folder
    elif search_type == "burst":
        centre_frequency, superevent, trigger_time, ifos = _read_burst_candidate(
            candidate
        )
        minimum_frequency = min(20, centre_frequency / 2)
        maximum_frequency = next_power_of_2(centre_frequency * 2)
        duration = 4
        extra_config_arguments = dict(
            frequency_domain_source_model="bilby.gw.source.sinegaussian",
            default_prior="PriorDict",
            time_marginalization=False,
            phase_marginalization=False,
            sampler_kwargs="FastTest",
        )
        prior_file = generate_burst_prior_from_template(
            minimum_frequency=minimum_frequency,
            maximum_frequency=maximum_frequency,
            outdir=outdir,
        )
    else:
        raise BilbyPipeError(
            "search_type should be either 'cbc' or 'burst', not {}".format(search_type)
        )

    config_dict = dict(
        label=gracedb,
        outdir=outdir,
        accounting="ligo.dev.o3.cbc.pe.lalinference",
        maximum_frequency=min(maximum_frequency, 4096),
        minimum_frequency=minimum_frequency,
        sampling_frequency=16384,
        trigger_time=trigger_time,
        detectors=ifos,
        channel_dict=channel_dict,
        deltaT=0.2,
        prior_file=prior_file,
        duration=duration,
        sampler="dynesty",
        sampler_kwargs=sampler_kwargs,
        webdir=webdir,
        local_generation=False,
        local_plot=False,
        transfer_files=False,
        create_summary=True,
        summarypages_arguments={"gracedb": gracedb},
        n_parallel=4,
        create_plots=True,
        plot_calibration=False,
        plot_corner=True,
        plot_marginal=False,
        plot_skymap=False,
        plot_waveform=False,
    )
    config_dict.update(extra_config_arguments)

    if online:
        config_dict["summarypages_arguments"]["no_ligo_skymap"] = True
    else:
        config_dict["summarypages_arguments"]["nsamples_for_skymap"] = 5000

    comment = (
        "# Configuration ini file generated from GraceDB "
        "for event id {} superevent id {}".format(gracedb, superevent)
    )
    filename = "{}/bilby_config.ini".format(outdir)
    _parser = parser.create_parser()
    _parser.write_to_file(
        filename=filename,
        args=config_dict,
        overwrite=True,
        include_description=False,
        exclude_default=True,
        comment=comment,
    )

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
    elif chirp_mass > 0.9:
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
    comp_min = roq_params["compmin"] / scale_factor

    if template is None:
        template = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "data_files/roq.prior.template"
        )

    with open(template, "r") as old_prior:
        prior_string = old_prior.read().format(
            mc_min=mc_min,
            mc_max=mc_max,
            comp_min=comp_min,
            d_min=distance_bounds[0],
            d_max=distance_bounds[1],
        )
    prior_file = os.path.join(outdir, "online.prior")
    with open(prior_file, "w") as new_prior:
        new_prior.write(prior_string)
    return prior_file


def generate_burst_prior_from_template(
    minimum_frequency, maximum_frequency, outdir, template=None
):
    """ Generate a prior file from a template and write it to file

    Parameters
    ----------
    minimum_frequency: float
        Minimum frequency for prior
    maximum_frequency: float
        Maximum frequency for prior
    outdir: str
        Path to the outdir (the prior is written to outdir/online.prior)
    template: str
        Alternative template file to use, otherwise the
        data_files/roq.prior.template file is used
    """
    if template is None:
        template = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "data_files/burst.prior.template",
        )

    with open(template, "r") as old_prior:
        prior_string = old_prior.read().format(
            minimum_frequency=minimum_frequency, maximum_frequency=maximum_frequency
        )
    prior_file = os.path.join(outdir, "online.prior")
    with open(prior_file, "w") as new_prior:
        new_prior.write(prior_string)
    return prior_file


def create_parser():
    parser = argparse.ArgumentParser(
        prog="bilby_pipe gracedb access",
        usage=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    group1 = parser.add_mutually_exclusive_group(required=True)
    group1.add_argument("--gracedb", type=str, help="GraceDB event id")
    group1.add_argument("--json", type=str, help="Path to json GraceDB file")
    parser.add_argument(
        "--online-pe",
        action="store_true",
        help=(
            "Flag to use online PE dedicated nodes."
            " To be used for online PE jobs only."
        ),
    )
    parser.add_argument(
        "--convert-to-flat-in-component-mass",
        action="store_true",
        default=False,
        help=(
            "Convert a flat-in chirp mass and mass-ratio prior file to flat \n"
            "in component mass during the post-processing. Note, the prior \n"
            "must be uniform in Mc and q with constraints in m1 and m2 for \n"
            "this to work. \n"
        ),
    )
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


def main(args=None, unknown_args=None):

    if args is None:
        args, unknown_args = create_parser().parse_known_args()
    elif unknown_args is None:
        unknown_args = []

    if len(unknown_args) > 1 and args.output == "ini":
        msg = [
            tcolors.WARNING,
            "Unrecognized arguments {}, these will be ignored".format(unknown_args),
            tcolors.END,
        ]
        logger.warning(" ".join(msg))

    outdir = args.outdir

    if args.json:
        json = args.json
        candidate = read_from_json(json)
        gracedb = candidate["graceid"]
        if outdir is None:
            outdir = "outdir_{}".format(gracedb)
        check_directory_exists_and_if_not_mkdir(outdir)
    elif args.gracedb:
        gracedb = args.gracedb
        gracedb_url = args.gracedb_url
        if outdir is None:
            outdir = "outdir_{}".format(gracedb)
        check_directory_exists_and_if_not_mkdir(outdir)
        candidate = read_from_gracedb(gracedb, gracedb_url, outdir)
    else:
        raise BilbyPipeError("Either gracedb ID or json file must be provided.")

    if args.webdir is not None:
        webdir = args.webdir
    else:
        webdir = os.path.join(outdir, "results_page")

    sampler_kwargs = args.sampler_kwargs
    channel_dict = CHANNEL_DICTS[args.channel_dict.lower()]

    if candidate["pipeline"].lower() in CBC_PIPELINES:
        search_type = "cbc"
        convert_to_flat_in_component_mass = args.convert_to_flat_in_component_mass
    elif candidate["pipeline"].lower() in BURST_PIPELINES:
        search_type = "burst"
        convert_to_flat_in_component_mass = False
    else:
        raise BilbyPipeError(
            "Candidate pipeline {} not recognised.".format(candidate["pipeline"])
        )

    filename = create_config_file(
        candidate=candidate,
        gracedb=gracedb,
        outdir=outdir,
        channel_dict=channel_dict,
        sampler_kwargs=sampler_kwargs,
        webdir=webdir,
        convert_to_flat_in_component_mass=convert_to_flat_in_component_mass,
        search_type=search_type,
        online=args.online_pe,
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
        if args.online_pe:
            arguments.append("--online-pe")
        if len(unknown_args) > 1:
            arguments = arguments + unknown_args
        run_command_line(arguments)
