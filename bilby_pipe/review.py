""" Tools for running the bilby review

Select from the options below to create an ini file which can be submitted using
bilby_pipe. Alternatively, use the --submit option to also submit the job

"""
import argparse
import json
import os
import sys
import time

import bilby
import bilby_pipe

from . import parser
from .utils import (
    DURATION_LOOKUPS,
    MAXIMUM_FREQUENCY_LOOKUPS,
    check_directory_exists_and_if_not_mkdir,
    logger,
    run_command_line,
)

fiducial_bbh_injections = {
    "128s": dict(
        chirp_mass=2.1,
        mass_ratio=0.9,
        a_1=0.04,
        a_2=0.01,
        tilt_1=1.0264673717225983,
        tilt_2=2.1701305583885513,
        phi_12=5.0962562029664955,
        phi_jl=2.518241237045709,
        luminosity_distance=100.0,
        dec=0.2205292600865073,
        ra=3.952677097361719,
        theta_jn=0.25,
        psi=2.6973435044499543,
        phase=3.686990398567503,
        geocent_time=-0.01,
    ),
    "4s": dict(
        chirp_mass=17.051544979894693,
        mass_ratio=0.3183945489993522,
        a_1=0.29526500202350264,
        a_2=0.23262056301313416,
        tilt_1=1.0264673717225983,
        tilt_2=2.1701305583885513,
        phi_12=5.0962562029664955,
        phi_jl=2.518241237045709,
        luminosity_distance=497.2983560174788,
        dec=0.2205292600865073,
        ra=3.952677097361719,
        theta_jn=1.8795187965094322,
        psi=2.6973435044499543,
        phase=3.686990398567503,
        geocent_time=0.040833669551002205,
    ),
    "high_mass": dict(
        chirp_mass=45.051544979894693,
        mass_ratio=0.9183945489993522,
        a_1=0.29526500202350264,
        a_2=0.23262056301313416,
        tilt_1=1.0264673717225983,
        tilt_2=2.1701305583885513,
        phi_12=5.0962562029664955,
        phi_jl=2.518241237045709,
        luminosity_distance=497.2983560174788,
        dec=0.2205292600865073,
        ra=3.952677097361719,
        theta_jn=1.8795187965094322,
        psi=2.6973435044499543,
        phase=3.686990398567503,
        geocent_time=0.040833669551002205,
    ),
}


fiducial_bns_injections = {
    "128s_tidal": dict(
        chirp_mass=1.486,
        mass_ratio=0.9,
        a_1=0.04,
        a_2=0.01,
        tilt_1=1.0264673717225983,
        tilt_2=2.1701305583885513,
        phi_12=5.0962562029664955,
        phi_jl=2.518241237045709,
        luminosity_distance=100.0,
        dec=0.2205292600865073,
        ra=3.952677097361719,
        theta_jn=0.25,
        psi=2.6973435044499543,
        phase=3.686990398567503,
        geocent_time=-0.01,
        lambda_1=1500,
        lambda_2=750,
    )
}


SAMPLER_KEYS = ["nlive", "walks", "nact", "maxmcmc"]


def get_default_top_level_dir():
    bilby_version_number = bilby.__version__.split(":")[0]
    bilby_git_hash = bilby.__version__.split(" ")[2]
    bilby_state = ["CLEAN", "UNCLEAN"]["UNCLEAN" in bilby.__version__]

    bilby_pipe_version_number = bilby_pipe.__long_version__.split(":")[0]
    bilby_pipe_git_hash = bilby_pipe.__long_version__.split(" ")[2]
    bilby_pipe_state = ["CLEAN", "UNCLEAN"]["UNCLEAN" in bilby_pipe.__long_version__]

    return "bilby{}-{}-{}_bilby_pipe{}-{}-{}".format(
        bilby_version_number,
        bilby_git_hash,
        bilby_state,
        bilby_pipe_version_number,
        bilby_pipe_git_hash,
        bilby_pipe_state,
    )


def get_top_level_dir(args):
    if args.directory:
        dirname = args.directory
    else:
        dirname = get_default_top_level_dir()
    check_directory_exists_and_if_not_mkdir(dirname)
    return dirname


def get_base_label(args, review_name):
    base_label = "{}_{}_{}_{}".format(
        review_name, args.prior, args.sampler, "-".join(args.marginalization)
    )
    if args.roq:
        base_label += "_ROQ"
    if args.zero_noise:
        base_label += "_zero-noise"

    for attr in SAMPLER_KEYS:
        if getattr(args, attr, None) is not None:
            base_label += "_{}{}".format(attr, getattr(args, attr))

    return base_label


def get_date_string():
    return time.strftime("%y%m%d %H:%M")


def write_ini_file(parser, filename, config_dict):
    parser.write_to_file(
        filename=filename,
        args=config_dict,
        overwrite=True,
        include_description=False,
        exclude_default=False,
        comment=(
            "Ini file written {}, command line args: {}".format(
                get_date_string(), " ".join(sys.argv[:])
            )
        ),
    )


def get_sampler_kwargs(args):
    sampler_kwargs = {
        attr: getattr(args, attr)
        for attr in SAMPLER_KEYS
        if getattr(args, attr, None) is not None
    }
    sampler_kwargs["n_check_point"] = 10000
    return sampler_kwargs


def get_default_setup(args, review_name):
    if args.duration is None:
        args.duration = DURATION_LOOKUPS[args.prior]

    top_level_dir = get_top_level_dir(args)
    base_label = get_base_label(args, review_name)
    rundir = "outdir_{}".format(base_label)
    filename = "{}/review_{}.ini".format(top_level_dir, base_label)

    base_dict = dict(
        label=base_label,
        accounting="ligo.dev.o3.cbc.pe.lalinference",
        detectors=str(args.detectors),
        outdir=rundir,
        deltaT=0.2,
        reference_frequency=args.reference_frequency,
        prior_file=args.prior,
        duration=args.duration,
        sampler=args.sampler,
        sampler_kwargs=get_sampler_kwargs(args),
        create_plots=None,
        n_parallel=args.n_parallel,
        sampling_frequency=4 * MAXIMUM_FREQUENCY_LOOKUPS[args.prior],
        maximum_frequency=MAXIMUM_FREQUENCY_LOOKUPS[args.prior],
        time_marginalization="time" in args.marginalization,
        distance_marginalization="distance" in args.marginalization,
        phase_marginalization="phase" in args.marginalization,
        generation_seed=args.generation_seed,
    )

    if args.roq:
        base_dict["likelihood-type"] = "ROQGravitationalWaveTransient"
        if args.roq_folder is None:
            base_dict["roq-folder"] = "/home/cbc/ROQ_data/IMRPhenomPv2/{}".format(
                args.prior
            )
        else:
            base_dict["roq-folder"] = args.roq_folder

    if args.zero_noise:
        base_dict["zero-noise"] = True

    return base_dict, rundir, filename


def fiducial_bbh(args):
    """ Review test: fiducial binary black hole in Gaussian noise

    Parameters
    ----------
    args: Namespace
        The command line arguments namespace object

    Returns
    -------
    filename: str
        A filename of the ini file generated
    """
    config_dict, rundir, filename = get_default_setup(args, "fiducial_bbh")
    config_dict["create_plots"] = True
    config_dict["create_summary"] = True
    config_dict["gaussian-noise"] = True
    config_dict["injection"] = True
    config_dict["n-injection"] = 1
    config_dict["injection-dict"] = str(fiducial_bbh_injections[args.prior])

    ini_parser = parser.create_parser()
    write_ini_file(ini_parser, filename, config_dict)
    return filename


def fiducial_bns(args):
    """ Review test: fiducial binary neutron star in Gaussian noise

    Parameters
    ----------
    args: Namespace
        The command line arguments namespace object

    Returns
    -------
    filename: str
        A filename of the ini file generated
    """
    config_dict, rundir, filename = get_default_setup(args, "fiducial_bns")
    config_dict["create_plots"] = True
    config_dict["create_summary"] = True
    config_dict["gaussian-noise"] = True
    config_dict["injection"] = True
    config_dict["n-injection"] = 1

    config_dict["frequency_domain_source_model"] = "lal_binary_neutron_star"
    config_dict["waveform-approximant"] = "IMRPhenomPv2_NRTidal"

    injection_filename = "{}/injection_file.json".format(rundir)
    with open(injection_filename, "w") as file:
        json.dump(
            dict(injections=fiducial_bns_injections[args.prior]),
            file,
            indent=2,
            cls=bilby.core.result.BilbyJsonEncoder,
        )
    config_dict["injection-file"] = injection_filename

    ini_parser = parser.create_parser()
    write_ini_file(ini_parser, filename, config_dict)
    return filename


def pp_test(args):
    """ Review test: pp-test

    Parameters
    ----------
    args: Namespace
        The command line arguments namespace object

    Returns
    -------
    filename: str
        A filename of the ini file generated
    """

    config_dict, rundir, filename = get_default_setup(args, "pp_test")

    config_dict["create_plots"] = False
    config_dict["injection"] = True
    config_dict["gaussian-noise"] = True
    config_dict["n-simulation"] = 100
    config_dict["sampler_kwargs"]["check_point_plot"] = False
    config_dict["postprocessing-executable"] = "bilby_pipe_pp_test"
    config_dict["postprocessing-arguments"] = "{}/result --outdir {}".format(
        rundir, rundir
    )
    ini_parser = parser.create_parser()
    write_ini_file(ini_parser, filename, config_dict)
    return filename


def get_args():
    parser = argparse.ArgumentParser(prog="bilby_pipe review script", usage=__doc__)

    parser.add_argument(
        "--submit", action="store_true", help="Build and submit the job"
    )
    parser.add_argument("--build", action="store_true", help="Build the job")
    parser.add_argument(
        "--directory",
        type=str,
        default=None,
        help="Set the top-level directory to use, defaults to a standardise naming scheme",
    )

    main_job_parser = parser.add_mutually_exclusive_group(required=True)
    main_job_parser.add_argument("--bbh", action="store_true", help="Fiducial BBH test")
    main_job_parser.add_argument("--bns", action="store_true", help="Fiducial BNS test")
    main_job_parser.add_argument("--pp-test", action="store_true", help="PP test test")

    parser.add_argument("--roq", action="store_true", help="Use ROQ likelihood")
    parser.add_argument(
        "--roq-folder", type=str, help="The ROQ folder to use, defaults to IMRPhenomPv2"
    )
    parser.add_argument(
        "--zero-noise", action="store_true", help="Run BBH and BNS test with zero noise"
    )
    parser.add_argument(
        "--prior",
        type=str,
        help="The default prior to use",
        choices=sorted(bilby_pipe.input.Input.get_default_prior_files()),
        required=True,
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Signal duration",
        choices=[4, 8, 16, 32, 64, 128],
    )
    parser.add_argument(
        "--sampler",
        type=str,
        default="dynesty",
        help="Sampler to use, default is dynesty",
    )
    parser.add_argument(
        "--marginalization",
        nargs="+",
        default=["time", "distance", "phase"],
        help=(
            "A space-separated list of {time, distance, phase} marginalization"
            "choices, default `--marginalization time distance phase`"
        ),
    )
    parser.add_argument(
        "--detectors",
        nargs="+",
        default=["H1", "L1"],
        help=("The detectors to use for simulating data, default [H1, L1]"),
    )
    parser.add_argument(
        "--nlive",
        type=int,
        default=None,
        help=("The number of live points to use, default None (use bilby defaults)"),
    )
    parser.add_argument(
        "--nact",
        type=int,
        default=None,
        help=("The nact (for dynesty only) to use, default None (use bilby defaults)"),
    )
    parser.add_argument(
        "--maxmcmc",
        type=int,
        default=None,
        help=("The maxmcmc to use, default None (use bilby defaults)"),
    )
    parser.add_argument(
        "--walks",
        type=int,
        default=None,
        help=("The walks (minimum mcmc) to use, default None (use bilby defaults)"),
    )
    parser.add_argument(
        "--n-parallel",
        type=int,
        default=4,
        help=("The number of parallel-processes to use, default 4"),
    )
    parser.add_argument(
        "--reference-frequency",
        type=int,
        default=100,
        help=("The reference frequency to run tests at, default 100"),
    )
    parser.add_argument(
        "--generation-seed",
        type=int,
        default=1010,
        help=("The seed used for generation: reproducible injections, default 1010"),
    )

    return parser.parse_args()


def main():

    args = get_args()

    # Standardise inputs
    args.marginalization = [xx.lower() for xx in args.marginalization]
    args.marginalization = sorted(args.marginalization)

    args.sampler = args.sampler.lower()

    if args.bbh:
        logger.info("Review test: fiducial BBH")
        filename = fiducial_bbh(args)
    elif args.bns:
        logger.info("Review test: fiducial BNS")
        filename = fiducial_bns(args)
    elif args.pp_test:
        logger.info("Review test: PP-test")
        filename = pp_test(args)
    else:
        raise Exception("No review test requested, see --help")

    if args.submit or args.build:
        dirname = os.path.dirname(filename)
        logger.info("Building and submitting the ini file {}".format(filename))
        arguments = ["bilby_pipe", filename]
        if args.submit:
            arguments.append("--submit")
        run_command_line(arguments, directory=dirname)
    else:
        logger.info("Built ini file {}".format(filename))
