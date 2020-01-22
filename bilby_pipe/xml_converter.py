#!/usr/bin/env python
"""
This a command line tool to convert XML injection files

"""
import argparse
import json
import os

import lalsimulation as lalsim
import pandas as pd
from gwpy.table import Table

import bilby

try:
    import ligo.lw  # noqa F401
except ImportError:
    raise ImportError("You do not have ligo.lw install: $ pip install python-liw-lw")


def xml_to_dataframe(prior_file, reference_frequency):
    table = Table.read(prior_file, format="ligolw", tablename="sim_inspiral")
    injection_values = {
        "mass_1": [],
        "mass_2": [],
        "luminosity_distance": [],
        "psi": [],
        "phase": [],
        "geocent_time": [],
        "ra": [],
        "dec": [],
        "theta_jn": [],
        "a_1": [],
        "a_2": [],
        "tilt_1": [],
        "tilt_2": [],
        "phi_12": [],
        "phi_jl": [],
    }
    for row in table:
        injection_values["mass_1"].append(float(row["mass1"]))
        injection_values["mass_2"].append(float(row["mass2"]))

        injection_values["luminosity_distance"].append(float(row["distance"]))
        injection_values["psi"].append(float(row["polarization"]))
        injection_values["phase"].append(float(row["coa_phase"]))
        injection_values["geocent_time"].append(float(row["geocent_end_time"]))
        injection_values["ra"].append(float(row["longitude"]))
        injection_values["dec"].append(float(row["latitude"]))

        args_list = [
            float(arg)
            for arg in [
                row["inclination"],
                row["spin1x"],
                row["spin1y"],
                row["spin1z"],
                row["spin2x"],
                row["spin2y"],
                row["spin2z"],
                row["mass1"],
                row["mass2"],
                reference_frequency,
                row["coa_phase"],
            ]
        ]
        (
            theta_jn,
            phi_jl,
            tilt_1,
            tilt_2,
            phi_12,
            a_1,
            a_2,
        ) = lalsim.SimInspiralTransformPrecessingWvf2PE(*args_list)
        injection_values["theta_jn"].append(theta_jn)
        injection_values["phi_jl"].append(phi_jl)
        injection_values["tilt_1"].append(tilt_1)
        injection_values["tilt_2"].append(tilt_2)
        injection_values["phi_12"].append(phi_12)
        injection_values["a_1"].append(a_1)
        injection_values["a_2"].append(a_2)

    injection_values = pd.DataFrame.from_dict(injection_values)
    return injection_values


def main():
    parser = argparse.ArgumentParser(
        prog="bilby_pipe_xml_converter", description=__doc__
    )
    parser.add_arg("xml_file", type=str, default=None, help="The xml file to convert")
    parser.add_arg(
        "--format",
        type=str,
        default="json",
        choices=["json", "dat"],
        help="The output injection format to use",
    )
    parser.add_arg(
        "--reference-frequency",
        type=float,
        default=None,
        help=("The reference frequency to use for converting from xml"),
        required=True,
    )

    args = parser.parse_args()
    injection_values = xml_to_dataframe(args.xml_file, args.reference_frequency)
    basename = os.path.splitext(args.xml_file)[0]
    path = basename + os.path.extsep + args.format
    if args.format == "json":
        injections = dict(injections=injection_values)
        with open(path, "w") as file:
            json.dump(
                injections, file, indent=2, cls=bilby.core.result.BilbyJsonEncoder
            )
    elif args.format == "dat":
        injection_values.to_csv(path, index=False, header=True, sep=" ")
