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


__all__ = ['Input']


class Input(object):
    def __init__(self, args, unknown_args):
        """ An object to hold all the inputs to bilby_pipe """
        self.known_detectors = ['H1', 'L1', 'V1']

        self.unknown_args = unknown_args
        self.ini = args.ini
        self.submit = args.submit
        self.outdir = args.outdir
        self.label = args.label
        self.accounting = args.accounting
        self.include_detectors = args.include_detectors
        self.coherence_test = args.coherence_test
        self.executable_library = args.executable_library
        self.executable = args.executable
        self.x509userproxy = args.X509
        if args.exe_help:
            self.executable_help()

    @property
    def include_detectors(self):
        """ A list of the detectors to include, e.g., ['H1', 'L1'] """
        return self._include_detectors

    @include_detectors.setter
    def include_detectors(self, include_detectors):
        if isinstance(include_detectors, str):
            det_list = self._split_string_by_space(include_detectors)
        elif isinstance(include_detectors, list):
            if len(include_detectors) == 1:
                det_list = self._split_string_by_space(include_detectors[0])
            else:
                det_list = include_detectors
        else:
            raise ValueError('Input `include_detectors` = {} not understood'
                             .format(include_detectors))

        det_list.sort()
        det_list = [det.upper() for det in det_list]

        for element in det_list:
            if element not in self.known_detectors:
                raise ValueError(
                    'include_detectors contains "{}" not in the known '
                    'detectors list: {} '.format(
                        element, self.known_detectors))
        self._include_detectors = det_list

    @staticmethod
    def _split_string_by_space(string):
        """ Converts "H1 L1" to ["H1", "L1"] """
        return string.split(' ')

    @property
    def outdir(self):
        return self._outdir

    @outdir.setter
    def outdir(self, outdir):
        utils.check_directory_exists_and_if_not_mkdir(outdir)
        self._outdir = outdir

    @property
    def executable(self):
        return self._executable

    @executable.setter
    def executable(self, executable):
        if os.path.isfile(executable) is False:
            executable = os.path.join(self.executable_library, executable)
            if os.path.isfile(executable):
                self._executable = executable
            else:
                raise ValueError('Unable to identify executable')
        else:
            self._executable = executable

    def executable_help(self):
        logger.info('Printing help message for given executable')
        os.system('{} --help'.format(self.executable))
        sys.exit()

    @property
    def x509userproxy(self):
        return self._x509userproxy

    @x509userproxy.setter
    def x509userproxy(self, x509userproxy):
        if x509userproxy is None:
            cert_alias = 'X509_USER_PROXY'
            cert_path = os.environ[cert_alias]
            new_cert_path = os.path.join(
                self.outdir, os.path.basename(cert_path))
            shutil.copyfile(cert_path, new_cert_path)
            self._x509userproxy = new_cert_path
        elif os.path.isfile(x509userproxy):
            self._x509userproxy = x509userproxy
        else:
            raise ValueError('Input X509 not a file or not understood')


def set_up_argument_parsing():
    parser = configargparse.ArgParser(
        usage='Generate submission scripts for the job',
        ignore_unknown_config_file_keys=True)
    parser.add('ini', type=str, is_config_file=True, help='The ini file')
    parser.add('--submit', action='store_true',
               help='If given, build and submit')
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
    parser.add('--X509', type=str, default=None,
               help=('If given, the path to the users X509 certificate file.'
                     'If not given, a copy of the file at the env. variable '
                     '$X509_USER_PROXY will be made in outdir and linked in '
                     'the condor jobs submission'))
    args, unknown_args = parser.parse_known_args()
    return args, unknown_args


def create_job_per_detector_set(inputs, dag, detectors):
    error = log = output = os.path.join(inputs.outdir, 'logs')
    submit = inputs.outdir
    extra_lines = 'accounting_group={}'.format(inputs.accounting)
    extra_lines += '\nx509userproxy={}'.format(inputs.x509userproxy)
    arguments = '--ini {}'.format(inputs.ini)
    name = inputs.label + '_' + ''.join(detectors)
    if isinstance(detectors, list):
        detectors = ' '.join(detectors)
    arguments += ' --detectors {}'.format(detectors)
    arguments += ' ' + ' '.join(inputs.unknown_args)
    pycondor.Job(
        name=name, executable=inputs.executable, extra_lines=extra_lines,
        output=output, log=log, error=error, submit=submit,
        arguments=arguments, dag=dag)


def main():
    inputs = Input(*set_up_argument_parsing())
    dag = pycondor.Dagman(name=inputs.label, submit=inputs.outdir)
    if inputs.coherence_test:
        for detector in inputs.include_detectors:
            create_job_per_detector_set(inputs, dag, detector)
    create_job_per_detector_set(inputs, dag, inputs.include_detectors)
    if inputs.submit:
        raise NotImplementedError(
            "This method is currently failing for unknown reasons")
        dag.build_submit()
    else:
        dag.build()
