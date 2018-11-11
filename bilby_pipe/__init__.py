"""
bilby_pipe
==========

bilby_pipe is a python3 tool for automating the process of running `bilby
<https://git.ligo.org/lscsoft/bilby>`_ for transient gravitational parameter
estimation on computing clusters.

"""
from .main import Input  # noqa
from .main import Dag  # noqa
from .main import parse_args  # noqa
from . import script_helper
