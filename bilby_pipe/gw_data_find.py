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


observatory_lookup = dict(H1='H', L1='L')

def gw_data_find(observatory, gps_start_time, gps_end_time, calibration):
    """ Builds a gw_data_find call and process output """
    logger.info('Building gw_data_find command line')

    observatory_code = observatory_lookup[observatory]

    dtype = '{}_HOFT_C0{}'.format(observatory, calibration)
    logger.info('Using LDRDataFind query type {}'.format(dtype))

    cl_list = ['gw_data_find']
    cl_list.append('--observatory {}'.format(observatory_code))
    cl_list.append('--gps-start-time {}'.format(gps_start_time))
    cl_list.append('--gps-end-time {}'.format(gps_end_time))
    cl_list.append('--type {}'.format(dtype))
    cl_list.append('--url-type file')
    cl = ' '.join(cl_list)
    output = run_commandline(cl)
    framefile = output.replace('file://localhost', '').rstrip('\n')
    return framefile

