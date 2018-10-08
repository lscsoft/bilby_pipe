import os
import logging
import subprocess
from bilby.gw.detector import get_empty_interferometer, PowerSpectralDensity


def run_commandline(cl, log_level=20, raise_error=True, return_output=True):
    """Run a string cmd as a subprocess, check for errors and return output.

    Parameters
    ----------
    cl: str
        Command to run
    log_level: int
        See https://docs.python.org/2/library/logging.html#logging-levels,
        default is '20' (INFO)

    """

    logger.log(log_level, 'Now executing: ' + cl)
    if return_output:
        try:
            out = subprocess.check_output(
                cl, stderr=subprocess.STDOUT, shell=True,
                universal_newlines=True)
        except subprocess.CalledProcessError as e:
            logger.log(log_level, 'Execution failed: {}'.format(e.output))
            if raise_error:
                raise
            else:
                out = 0
        os.system('\n')
        return(out)
    else:
        process = subprocess.Popen(cl, shell=True)
        process.communicate()


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

    if not all([type(h) == logging.StreamHandler for h in logger.handlers]):
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

    version_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'bilby_pipe/.version')
    with open(version_file, 'r') as f:
        version = f.readline().rstrip()

    if print_version:
        logger.info('Running bilby_pipe version: {}'.format(version))


def load_data_from_cache_file(
        cache_file, trigger_time, segment_duration, psd_duration,
        channel_name=None):
    data_set = False
    psd_set = False
    segment_start = trigger_time - segment_duration + 1
    psd_start = segment_start - psd_duration - 4
    with open(cache_file, 'r') as ff:
        lines = ff.readlines()
        ifo_name = lines[0][0] + '1'
        ifo = get_empty_interferometer(ifo_name)
        for line in lines:
            line = line.strip()
            _, _, frame_start, frame_duration, frame_name = line.split(' ')
            frame_start = float(frame_start)
            frame_duration = float(frame_duration)
            if frame_name[:4] == 'file':
                frame_name = frame_name[16:]
            if not data_set & (frame_start < segment_start) &\
                    (segment_start < frame_start + frame_duration):
                ifo.set_strain_data_from_frame_file(
                    frame_name, 4096, segment_duration,
                    start_time=segment_start,
                    channel=channel_name, buffer_time=0)
                data_set = True
            if not psd_set & (frame_start < psd_start) &\
                    (psd_start + psd_duration < frame_start + frame_duration):
                ifo.power_spectral_density =\
                    PowerSpectralDensity.from_frame_file(
                        frame_name, psd_start_time=psd_start,
                        psd_duration=psd_duration,
                        channel=channel_name, sampling_frequency=4096)
                psd_set = True
    if data_set and psd_set:
        return ifo
    elif not data_set:
        logging.warning('Data not loaded for {}'.format(ifo.name))
    elif not psd_set:
        logging.warning('PSD not created for {}'.format(ifo.name))


setup_logger()
logger = logging.getLogger('bilby_pipe')
