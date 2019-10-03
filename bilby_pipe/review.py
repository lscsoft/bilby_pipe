""" Tools for running review accessed through bilby_pipe_review """
import argparse
import json
import time

import bilby
import bilby_pipe
from .utils import (
    check_directory_exists_and_if_not_mkdir,
    DURATION_LOOKUPS,
    MAXIMUM_FREQUENCY_LOOKUPS,
    run_command_line,
)
from . import parser

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


def get_date_string():
    return time.strftime("%y%m%d_%H%M")


def get_default_setup(args, review_name):
    if args.duration is None:
        args.duration = DURATION_LOOKUPS[args.prior]

    base_label = "{}_{}".format(review_name, args.prior)
    if args.roq:
        base_label += "_ROQ"
    if args.zero_noise:
        base_label += "_zero-noise"
    label_with_date = "{}_{}".format(base_label, get_date_string())

    rundir = "outdir_{}".format(base_label)
    check_directory_exists_and_if_not_mkdir(rundir)
    filename = "{}/review_{}.ini".format(rundir, label_with_date)

    base_dict = dict(
        label=label_with_date,
        accounting="ligo.dev.o3.cbc.pe.lalinference",
        detectors="[H1, L1]",
        outdir=rundir,
        deltaT=0.2,
        prior_file=args.prior,
        duration=args.duration,
        sampler="dynesty",
        sampler_kwargs="{n_check_point: 10000}",
        create_plots=None,
        sampling_frequency=4 * MAXIMUM_FREQUENCY_LOOKUPS[args.prior],
        maximum_frequency=MAXIMUM_FREQUENCY_LOOKUPS[args.prior],
        time_marginalization=True,
        distance_marginalization=True,
        phase_marginalization=True,
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
    config_dict["generation-seed"] = 1010
    config_dict["n-parallel"] = 4
    if args.prior == "128s":
        config_dict["sampler_kwargs"] = "{walks=800, n_check_point=10000}"

    injection_filename = "{}/injection_file.json".format(rundir)
    with open(injection_filename, "w") as file:
        json.dump(
            dict(injections=fiducial_bbh_injections[args.prior]),
            file,
            indent=2,
            cls=bilby.core.result.BilbyJsonEncoder,
        )
    config_dict["injection-file"] = injection_filename

    _parser = parser.create_parser()
    _parser.write_to_file(
        filename=filename,
        args=config_dict,
        overwrite=True,
        include_description=False,
        exclude_default=True,
    )
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
    config_dict["generation-seed"] = 1010
    config_dict["n-parallel"] = 4

    config_dict["frequency_domain_source_model"] = "lal_binary_neutron_star"
    config_dict["waveform-approximant"] = "IMRPhenomPv2_NRTidal"

    config_dict["sampler_kwargs"] = "{walks=500, n_check_point=10000}"

    injection_filename = "{}/injection_file.json".format(rundir)
    with open(injection_filename, "w") as file:
        json.dump(
            dict(injections=fiducial_bns_injections[args.prior]),
            file,
            indent=2,
            cls=bilby.core.result.BilbyJsonEncoder,
        )
    config_dict["injection-file"] = injection_filename

    _parser = parser.create_parser()
    _parser.write_to_file(
        filename=filename,
        args=config_dict,
        overwrite=True,
        include_description=False,
        exclude_default=True,
    )
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
    config_dict["reference_frequency"] = 100
    if args.prior in ["128s", "128s_tidal"]:
        config_dict[
            "sampler_kwargs"
        ] = "{check_point_plot=False, walks=800, n_check_point=10000}"
    else:
        config_dict["sampler_kwargs"] = "{check_point_plot=False, n_check_point=10000}"
    config_dict["postprocessing-executable"] = "bilby_pipe_pp_test"
    config_dict["postprocessing-arguments"] = "{}/result --outdir {}".format(
        rundir, rundir
    )
    filename = "review_{}.ini".format(config_dict["label"])
    _parser = parser.create_parser()
    _parser.write_to_file(
        filename=filename,
        args=config_dict,
        overwrite=True,
        include_description=False,
        exclude_default=True,
    )
    return filename


def main():
    parser = argparse.ArgumentParser(prog="bilby_pipe review script", usage="")
    parser.add_argument("--submit", action="store_true", help="Submit the job")
    parser.add_argument("--bbh", action="store_true", help="Fiducial BBH test")
    parser.add_argument("--bns", action="store_true", help="Fiducial BNS test")
    parser.add_argument("--roq", action="store_true", help="Use ROQ likelihood")
    parser.add_argument(
        "--roq-folder", type=str, help="The ROQ folder to use, defaults to IMRPhenomPv2"
    )
    parser.add_argument("--pp-test", action="store_true", help="PP test test")
    parser.add_argument(
        "--zero-noise", action="store_true", help="Run BBH and BNS test with zero noise"
    )
    parser.add_argument(
        "--prior",
        type=str,
        help="The default prior to use",
        choices=sorted(bilby_pipe.input.Input.get_default_prior_files()),
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Signal duration",
        choices=[4, 8, 16, 32, 64, 128],
    )
    args = parser.parse_args()

    if args.bbh:
        filename = fiducial_bbh(args)
    elif args.bns:
        filename = fiducial_bns(args)
    elif args.pp_test:
        filename = pp_test(args)
    else:
        raise Exception("No review test requested, see --help")

    arguments = ["bilby_pipe", filename]
    if args.submit:
        arguments.append("--submit")
    run_command_line(arguments)
