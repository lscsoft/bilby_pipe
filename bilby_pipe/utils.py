"""
A set of generic utilities used in bilby_pipe
"""
import os
import sys
import logging


def check_directory_exists_and_if_not_mkdir(directory):
    """ Checks if the given directory exists and creates it if it does not exist

    Parameters
    ----------
    directory: str
        Name of the directory

    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.debug('Making directory {}'.format(directory))
    else:
        logger.debug('Directory {} exists'.format(directory))


def setup_logger(outdir=None, label=None, log_level='INFO',
                 print_version=False):
    """ Setup logging output: call at the start of the script to use

    Parameters
    ----------
    outdir, label: str
        If supplied, write the logging output to outdir/label.log
    log_level: str, optional
        ['debug', 'info', 'warning']
        Either a string from the list above, or an integer as specified
        in https://docs.python.org/2/library/logging.html#logging-levels
    print_version: bool
        If true, print version information
    """

    if '-v' in sys.argv:
        log_level = 'DEBUG'

    if type(log_level) is str:
        try:
            level = getattr(logging, log_level.upper())
        except AttributeError:
            raise ValueError('log_level {} not understood'.format(log_level))
    else:
        level = int(log_level)

    logger = logging.getLogger('bilby_pipe')
    logger.propagate = False
    logger.setLevel(level)

    streams = [type(h) == logging.StreamHandler for h in logger.handlers]
    if len(streams) == 0 or not all(streams):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(name)s %(levelname)-8s: %(message)s',
            datefmt='%H:%M'))
        stream_handler.setLevel(level)
        logger.addHandler(stream_handler)

    if any([type(h) == logging.FileHandler for h in logger.handlers]) is False:
        if label:
            if outdir:
                check_directory_exists_and_if_not_mkdir(outdir)
            else:
                outdir = '.'
            log_file = '{}/{}.log'.format(outdir, label)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)-8s: %(message)s', datefmt='%H:%M'))

            file_handler.setLevel(level)
            logger.addHandler(file_handler)

    for handler in logger.handlers:
        handler.setLevel(level)

    if print_version:
        version = get_version_information()
        logger.info('Running bilby_pipe version: {}'.format(version))


def get_version_information():
    version_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'bilby_pipe/.version')
    try:
        with open(version_file, 'r') as f:
            return f.readline().rstrip()
    except EnvironmentError:
        print("No version information file '.version' found")


setup_logger(print_version=True)
logger = logging.getLogger('bilby_pipe')
