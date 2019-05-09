#!/usr/bin/env python
""" Module for determining the appropriate prior automatically """


def determine_prior_file_from_parameters(mchirp):
    """ Determine appropriate prior from chirp mass

    Parameters
    ----------
    mchirp: float
        The chirp mass of the source (in solar masses)

    Returns
    -------
    prior: str
        A string repesentation of the appropriate prior to use
    """

    if mchirp > 45:
        prior = "high_mass"
    elif mchirp > 13.53:
        prior = "4s"
    elif mchirp > 8.73:
        prior = "8s"
    elif mchirp > 5.66:
        prior = "16s"
    elif mchirp > 3.68:
        prior = "32s"
    elif mchirp > 2.39:
        prior = "64s"
    else:
        prior = "128s"

    return prior
