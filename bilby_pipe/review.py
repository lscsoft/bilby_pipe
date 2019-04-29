""" Tools for running review accessed through bilby_pipe_review """
import argparse
import json
import os
import subprocess
import time

import bilby
import bilby_pipe


def get_label():
    return time.strftime("%y%m%d_%H%M")


def get_default_config_dict(args):
    base_dict = dict(
        label=get_label(),
        outdir=None,
        accounting="ligo.dev.o3.cbc.pe.lalinference",
        detectors="[H1, L1]",
        deltaT=0.2,
        prior_file=args.prior,
        duration=args.duration,
        sampler="dynesty",
        sampler_kwargs="{nlive: 1000, walks: 100, n_check_point: 5000}",
        create_plots=None,
        time_marginalization=True,
        distance_marginalization=True,
        phase_marginalization=True,
    )

    if args.roq:
        base_dict["likelihood-type"] = "ROQGravitationalWaveTransient"
        base_dict["roq-folder"] = "/home/cbc/ROQ_data"

    return base_dict


def write_config_file(config_dict):
    if None in config_dict.values():
        raise ValueError("config-dict is not complete")

    filename = "review_{}_{}.ini".format(config_dict["outdir"], config_dict["label"])
    with open(filename, "w+") as file:
        for key, val in config_dict.items():
            print("{}={}".format(key, val), file=file)

    return filename


def run_command_line(arguments):
    print("\nRunning command $ {}\n".format(" ".join(arguments)))
    subprocess.call(arguments)


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
    config_dict = get_default_config_dict(args)
    config_dict["outdir"] = "fiducial_bbh"
    config_dict["create_plots"] = True
    config_dict["trigger-time"] = 0
    config_dict["gaussian-noise"] = True
    config_dict["injection"] = True
    config_dict["n-injection"] = 1
    config_dict["generation-seed"] = 1010
    config_dict["sampling-seed"] = 4567

    parameters = dict(
        chirp_mass=17.051544979894693,
        mass_ratio=0.3183945489993522,
        a_1=0.29526500202350264,
        a_2=0.23262056301313416,
        tilt_1=1.0264673717225983,
        tilt_2=2.1701305583885513,
        phi_12=5.0962562029664955,
        phi_jl=2.518241237045709,
        luminosity_distance=797.2983560174788,
        dec=0.2205292600865073,
        ra=3.952677097361719,
        theta_jn=1.8795187965094322,
        psi=2.6973435044499543,
        phase=3.686990398567503,
        geocent_time=0.040833669551002205,
    )
    injection_filename = "{}/injection_file.json".format(config_dict["outdir"])
    os.mkdir(config_dict["outdir"])
    with open(injection_filename, "w") as file:
        json.dump(
            dict(injections=parameters),
            file,
            indent=2,
            cls=bilby.core.result.BilbyJsonEncoder,
        )
    config_dict["injection-file"] = injection_filename

    filename = write_config_file(config_dict)
    return filename


def fiducial_bns(args):
    raise Exception("Not implemented yet")


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
    outdir = "outdir_pp_test"

    config_dict = get_default_config_dict(args)
    config_dict["outdir"] = outdir
    config_dict["create_plots"] = False
    config_dict["trigger-time"] = 0
    config_dict["injection"] = True
    config_dict["n-injection"] = 100
    config_dict["gaussian-noise"] = True
    config_dict["postprocessing-executable"] = "bilby_pipe_pp_test"
    config_dict["postprocessing-arguments"] = "{}/result --outdir {}".format(
        outdir, outdir
    )
    filename = write_config_file(config_dict)
    return filename


def main():
    parser = argparse.ArgumentParser(prog="bilby_pipe review script", usage="")
    parser.add_argument("--submit", action="store_true", help="Submit the job")
    parser.add_argument("--bbh", action="store_true", help="Fiducial BBH test")
    parser.add_argument("--bns", action="store_true", help="Fiducial BNS test")
    parser.add_argument("--roq", action="store_true", help="Use ROQ likelihood")
    parser.add_argument("--pp-test", action="store_true", help="PP test test")
    parser.add_argument(
        "--prior",
        type=str,
        help="The default prior to use",
        choices=sorted(bilby_pipe.input.Input.get_default_prior_files()),
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=4,
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