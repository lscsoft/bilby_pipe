"""
bilby_pipe
==========

bilby_pipe is a python3 tool for automating the process of running `bilby
<https://git.ligo.org/lscsoft/bilby>`_ for transient gravitational parameter
estimation on computing clusters.

"""

from . import main
from . import webpages
from . import bilbyargparser
from . import utils

__version__ = utils.get_version_information()

