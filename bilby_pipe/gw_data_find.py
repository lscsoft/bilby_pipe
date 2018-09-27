import subprocess
import os
from .utils import logger

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


def gw_data_find(observatory, gps_start_time, duration, calibration,
                 outdir='.'):
    """ Builds a gw_data_find call and process output

    Parameters
    ----------
    observatory: str, {H1, L1}
        Observatory description
    gps_start_time: float
        The start time in gps to look for data
    duration: int
        The duration (integer) in s
    calibrartion: int {1, 2}
        Use C01 or C02 calibration
    outdir: string
        A path to the directory where output is stored

    Returns
    -------
    output_cache_file: str
        Path to the output cache file

    """
    logger.info('Building gw_data_find command line')

    observatory_lookup = dict(H1='H', L1='L')
    observatory_code = observatory_lookup[observatory]

    dtype = '{}_HOFT_C0{}'.format(observatory, calibration)
    logger.info('Using LDRDataFind query type {}'.format(dtype))

    cache_file = '{}-{}_CACHE-{}-{}.lcf'.format(
        observatory, dtype, gps_start_time, duration)
    output_cache_file = os.path.join(outdir, cache_file)

    gps_end_time = gps_start_time + duration

    cl_list = ['gw_data_find']
    cl_list.append('--observatory {}'.format(observatory_code))
    cl_list.append('--gps-start-time {}'.format(gps_start_time))
    cl_list.append('--gps-end-time {}'.format(gps_end_time))
    cl_list.append('--type {}'.format(dtype))
    cl_list.append('--output {}'.format(output_cache_file))
    cl_list.append('--url-type file')
    cl_list.append('--lal-cache')
    cl = ' '.join(cl_list)
    out = run_commandline(cl)
    return output_cache_file
