#!/usr/bin/env python

import os
import subprocess
import sys
from pathlib import Path

from setuptools import setup

# check that python version is 3.5 or above
python_version = sys.version_info
print("Running Python version %s.%s.%s" % python_version[:3])
if python_version < (3, 5):
    sys.exit("Python < 3.5 is not supported, aborting setup")
print("Confirmed Python version 3.5.0 or above")


def write_version_file(version):
    """ Writes a file with version information to be used at run time

    Parameters
    ----------
    version: str
        A string containing the current version information

    Returns
    -------
    version_file: str
        A path to the version file (relative to the bilby_pipe
        package directory)
    """
    version_file = Path("bilby_pipe") / ".version"

    try:
        git_log = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%h %ai"]
        ).decode("utf-8")
        git_diff = (
            subprocess.check_output(["git", "diff", "."])
            + subprocess.check_output(["git", "diff", "--cached", "."])
        ).decode("utf-8")
    except subprocess.CalledProcessError as exc:  # git calls failed
        # we already have a version file, let's use it
        if version_file.is_file():
            return version_file.name
        # otherwise error out
        exc.args = (
            "unable to obtain git version information, and {} doesn't "
            "exist, cannot continue ({})".format(version_file, str(exc)),
        )
        raise
    else:
        git_version = "{}: ({}) {}".format(
            version, "UNCLEAN" if git_diff else "CLEAN", git_log.rstrip()
        )
        print("parsed git version info as: {!r}".format(git_version))

    with open(version_file, "w") as f:
        print(git_version, file=f)
        print("created {}".format(version_file))

    return version_file.name


def get_long_description():
    """ Finds the README and reads in the description """
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, "README.rst")) as f:
        long_description = f.read()
    return long_description


VERSION = "0.3.10"
version_file = write_version_file(VERSION)
long_description = get_long_description()

setup(
    name="bilby_pipe",
    description="Automating the running of bilby for gravitational wave signals",
    long_description=long_description,
    url="https://lscsoft.docs.ligo.org/bilby_pipe/index.html",
    author="Gregory Ashton, Isobel Romero-Shaw, Colm Talbot, Charlie Hoy, Shanika Galaudage",
    author_email="gregory.ashton@ligo.org",
    license="MIT",
    version=VERSION,
    package_data={"bilby_pipe": [version_file, "data_files/*"]},
    packages=["bilby_pipe"],
    install_requires=[
        "future",
        "pycondor>=0.5",
        "configargparse",
        "ligo-gracedb",
        "bilby>=0.6.5",
        "scipy>=1.2.0",
        "gwpy",
        "matplotlib",
        "numpy",
        "tqdm",
        "corner",
        "dynesty>=1.0.0",
        "pesummary>=0.2.4",
        "jinja2",
    ],
    entry_points={
        "console_scripts": [
            "bilby_pipe=bilby_pipe.main:main",
            "bilby_pipe_generation=bilby_pipe.data_generation:main",
            "bilby_pipe_analysis=bilby_pipe.data_analysis:main",
            "bilby_pipe_create_injection_file=bilby_pipe.create_injections:main",
            "bilby_pipe_xml_converter=bilby_pipe.xml_converter:main",
            "bilby_pipe_pp_test=bilby_pipe.pp_test:main",
            "bilby_pipe_review=bilby_pipe.review:main",
            "bilby_pipe_plot=bilby_pipe.plot:main",
            "bilby_pipe_plot_calibration=bilby_pipe.plot:plot_calibration",
            "bilby_pipe_plot_corner=bilby_pipe.plot:plot_corner",
            "bilby_pipe_plot_marginal=bilby_pipe.plot:plot_marginal",
            "bilby_pipe_plot_skymap=bilby_pipe.plot:plot_skymap",
            "bilby_pipe_plot_waveform=bilby_pipe.plot:plot_waveform",
            "bilby_pipe_gracedb=bilby_pipe.gracedb:main",
            "bilby_pipe_write_default_ini=bilby_pipe.parser:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
    ],
)
