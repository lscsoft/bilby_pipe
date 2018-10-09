|pipeline status| |coverage report|
bilby_pipe
==========

A package for automating transient gravitational wave parameter estimation

Installation
------------

Clone the repository then run::

   $ python setup.py install

This will install all dependencies. Currently, it assumes you have access to a
working version of `gw_data_find` without explicitly pointing it to the server
(i.e., that you are working on one of the LDG clusters).

Example
-------

In this example, we call `bilby_pipe` for the gracedb event G184098,
which is GW150914. Other required inputs are the executable to run, and the
accounting group.

First, create an ini file::

   executable = bbh_from_gracedb.py
   accounting = ligo.dev.o3.cbc.pe.lalinference
   include-detectors = [H1, L1]

   coherence-test = True
   duration=4
   outdir=bilby_output
   sampler = dynesty
   sampler-kwargs = {'nlive': 100}

Then submit with::

   $ bilby_pipe test.ini --gracedb G184098

.. |pipeline status| image:: https://git.ligo.org/Monash/bilby_pipe/badges/master/pipeline.svg
   :target: https://git.ligo.org/Monash/bilby_pipe/commits/master
.. |coverage report| image:: https://monash.docs.ligo.org/bilby_pipe/coverage_badge.svg
   :target: https://monash.docs.ligo.org/bilby_pipe/htmlcov/

