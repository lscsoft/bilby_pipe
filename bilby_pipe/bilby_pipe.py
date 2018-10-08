#!/usr/bin/env python
"""
"""
import os
import sys

import configargparse

from .utils import logger
from . import utils


def set_up_argument_parsing():
    parser = configargparse.ArgParser(
        usage='Generate submission scripts for the job',
        ignore_unknown_config_file_keys=True)
    parser.add('--ini', type=str, required=True, is_config_file=True,
               help='The ini file')
    parser.add('--exe-help', action='store_true',
               help='Print the help function for the executable')
    parser.add('--label', type=str, default='LABEL',
               help='The output label')
    parser.add('--outdir', type=str, default='bilby_outdir',
               help='The output directory')
    parser.add('--detectors', nargs='+',
               help='The detector names')
    parser.add('--accounting', type=str, required=True,
               help='The accounting group to use')
    parser.add('--executable', type=str, required=True,
               help=('Either a path to the executable or the name of '
                     'the execuatable in the library'))
    parser.add('--executable_library', type=str,
               default='/home/gregory.ashton/bilby_pipe/lib_scripts/',
               help='The executable library')
    return parser.parse_args()


def create_submit(args):
    import pycondor
    error = log = output = os.path.join(args.outdir, 'logs')
    submit = args.outdir
    extra_lines = 'accounting_group={}'.format(args.accounting)
    arguments = '--ini {}'.format(args.ini)
    job = pycondor.Job(
        name=args.label, executable=args.executable, extra_lines=extra_lines,
        output=output, log=log, error=error, submit=submit,
        arguments=arguments)
    job.build()


def setup_executable(args):
    if os.path.isfile(args.executable) is False:
        executable = os.path.join(args.executable_library, args.executable)
        if os.path.isfile(executable):
            args.executable = executable
        else:
            raise ValueError('Unable to identify executable')
    if args.exe_help:
        logger.info('Printing help message for given executable')
        os.system('{} --help'.format(args.executable))
        sys.exit()
    return args


def main():
    args = set_up_argument_parsing()
    utils.check_directory_exists_and_if_not_mkdir(args.outdir)
    args = setup_executable(args)
    create_submit(args)
