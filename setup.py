#!/usr/bin/env python

import os
import sys
from setuptools import setup
import subprocess

# check that python version is 3.5 or above
python_version = sys.version_info
print("Running Python version %s.%s.%s" % python_version[:3])
if python_version < (3, 5):
    sys.exit("Python < 3.5 is not supported, aborting setup")
else:
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
        A path to the version file

    """
    try:
        git_log = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%h %ai"]
        ).decode("utf-8")
        git_diff = (
            subprocess.check_output(["git", "diff", "."])
            + subprocess.check_output(["git", "diff", "--cached", "."])
        ).decode("utf-8")
        if git_diff == "":
            git_status = "(CLEAN) " + git_log
        else:
            git_status = "(UNCLEAN) " + git_log
    except Exception as e:
        print("Unable to obtain git version information, exception: {}".format(e))
        git_status = ""

    version_file = ".version"
    if os.path.isfile(version_file) is False:
        with open("bilby_pipe/" + version_file, "w+") as f:
            f.write("{}: {}".format(version, git_status))

    return version_file


def get_long_description():
    """ Finds the README and reads in the description """
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, "README.rst")) as f:
        long_description = f.read()
    return long_description


VERSION = "0.0.4"
version_file = write_version_file(VERSION)
long_description = get_long_description()

setup(
    name="bilby_pipe",
    description="Automating the running of bilby for gravitational wave signals",
    long_description=long_description,
    url="https://lscsoft.docs.ligo.org/bilby_pipe/index.html",
    author="Gregory Ashton, Isobel Romero-Shaw, Colm Talbot, Charlie Hoy",
    author_email="gregory.ashton@ligo.org",
    license="MIT",
    version=VERSION,
    package_data={"bilby_pipe": [version_file, "templates/*html"]},
    packages=["bilby_pipe"],
    install_requires=[
        "future",
        "pycondor>=0.5",
        "configargparse",
        "ligo-gracedb",
        "gwdatafind",
        "urllib3",
        "bilby>=0.4.1",
        "deepdish",
        "pesummary",
    ],
    entry_points={
        "console_scripts": [
            "bilby_pipe=bilby_pipe.main:main",
            "bilby_pipe_generation=bilby_pipe.data_generation:main",
            "bilby_pipe_analysis=bilby_pipe.data_analysis:main",
            "bilby_pipe_singularity=bilby_pipe.singularity:main",
            "bilby_pipe_create_injection_file=bilby_pipe.create_injections:main",
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
