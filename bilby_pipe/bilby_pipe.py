#!/usr/bin/env python
"""
"""
import os
import sys
import shutil

import configargparse
import pycondor

from .utils import logger
from . import utils


def set_up_argument_parsing():
    parser = configargparse.ArgParser(
        usage='Generate submission scripts for the job',
        ignore_unknown_config_file_keys=True)
    parser.add('ini', type=str, is_config_file=True, help='The ini file')
    parser.add('--exe-help', action='store_true',
               help='Print the help function for the executable')
    parser.add('--include-detectors', nargs='+', default=['H1', 'L1'],
               help='The names of detectors to include {H1, L1}')
    parser.add('--coherence-test', action='store_true')
    parser.add('--label', type=str, default='LABEL',
               help='The output label')
    parser.add('--outdir', type=str, default='bilby_outdir',
               help='The output directory')
    parser.add('--accounting', type=str, required=True,
               help='The accounting group to use')
    parser.add('--executable', type=str, required=True,
               help=('Either a path to the executable or the name of '
                     'the execuatable in the library'))
    parser.add('--executable_library', type=str,
               default='/home/gregory.ashton/bilby_pipe/lib_scripts/',
               help='The executable library')
    args, unknown_args = parser.parse_known_args()
    return args, unknown_args


def create_job_per_detector_set(args, detectors, dag, unknown_args):
    error = log = output = os.path.join(args.outdir, 'logs')
    submit = args.outdir
    extra_lines = 'accounting_group={}'.format(args.accounting)
    new_cert_path = setup_certificates(args.outdir)
    extra_lines += '\nx509userproxy={}'.format(new_cert_path)
    arguments = '--ini {}'.format(args.ini)
    name = args.label + '_' + ''.join(detectors)
    if isinstance(detectors, list):
        detectors = ' '.join(detectors) 
    arguments += ' --detectors {}'.format(detectors)
    arguments += ' ' + ' '.join(unknown_args)
    pycondor.Job(
        name=name, executable=args.executable, extra_lines=extra_lines,
        output=output, log=log, error=error, submit=submit,
        arguments=arguments, dag=dag)


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


def setup_certificates(outdir):
    cert_alias = 'X509_USER_PROXY'
    cert_path = os.environ[cert_alias]
    new_cert_path = os.path.join(outdir, os.path.basename(cert_path))
    shutil.copyfile(cert_path, new_cert_path)
    return new_cert_path


def main():
    args, unknown_args = set_up_argument_parsing()
    utils.check_directory_exists_and_if_not_mkdir(args.outdir)
    args = setup_executable(args)
    detectors = ' '.join(args.include_detectors).split(' ')
    dag = pycondor.Dagman(name=args.label, submit=args.outdir)
    if args.coherence_test:
        for detector in detectors:
            create_job_per_detector_set(args, detector, dag, unknown_args)
    create_job_per_detector_set(args, detectors, dag, unknown_args)
    dag.build()
