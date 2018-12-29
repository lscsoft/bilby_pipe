#!/usr/bin/env python

from setuptools import setup
import subprocess
from os import path
import sys

# check that python version is 3.5 or above
python_version = sys.version_info
print('Running Python version %s.%s.%s' % python_version[:3])
if python_version < (3, 5):
    sys.exit('Python < 3.5 is not supported, aborting setup')
else:
    print('Confirmed Python version 3.5.0 or above')


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
            ['git', 'log', '-1', '--pretty=%h %ai']).decode('utf-8')
        git_diff = (subprocess.check_output(['git', 'diff', '.']) +
                    subprocess.check_output(
                        ['git', 'diff', '--cached', '.'])).decode('utf-8')
        if git_diff == '':
            git_status = '(CLEAN) ' + git_log
        else:
            git_status = '(UNCLEAN) ' + git_log
    except Exception as e:
        print("Unable to obtain git version information, exception: {}"
              .format(e))
        git_status = ''

    version_file = '.version'
    if path.isfile(version_file) is False:
        with open('bilby_pipe/' + version_file, 'w+') as f:
            f.write('{}: {}'.format(version, git_status))

    return version_file


def get_long_description():
    """ Finds the README and reads in the description """
    here = path.abspath(path.dirname(__file__))
    with open(path.join(here, 'README.rst')) as f:
            long_description = f.read()
    return long_description


version = '0.0.1'
version_file = write_version_file(version)
long_description = get_long_description()

setup(name='bilby_pipe',
      description='',
      long_description=long_description,
      url='',
      author='',
      author_email='',
      license='',
      version=version,
      package_data={'bilby_pipe': [version_file, 'templates/*html']},
      packages=['bilby_pipe'],
      install_requires=[
          'future',
          'pycondor>=0.5',
          'configargparse',
          'pesummary',
          'ligo-gracedb',
          'gwdatafind'],
      entry_points={
          'console_scripts': [
              'bilby_pipe=bilby_pipe.main:main',
              'bilby_pipe_generation=bilby_pipe.data_generation:main',
              'bilby_pipe_analysis=bilby_pipe.data_analysis:main',
              'bilby_pipe_create_injection_file=bilby_pipe.create_injections:main']},
      classifiers=[
          "Programming Language :: Python :: 3.7",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent"])
