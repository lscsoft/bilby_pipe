|pipeline status| |coverage report|

bilby_pipe
==========

A package for automating transient gravitational wave parameter estimation

-  `Installation
   instructions <https://lscsoft.docs.ligo.org/bilby_pipe/installation.html>`__
-  `Documentation <https://lscsoft.docs.ligo.org/bilby_pipe/index.html>`__
-  `Issue tracker <https://git.ligo.org/lscsoft/bilby/issues>`__


Documentation including a basic example can be found in the `project wiki <https://git.ligo.org/lscsoft/bilby_pipe/wikis/home>`_. 
Please add issues (including feature requests) to the `issue tracker <https://git.ligo.org/lscsoft/bilby_pipe/issues>`_.


Installation
------------

Clone the repository then run

.. code-block:: console

   $ python setup.py install

This will install all dependencies. Currently, it assumes you have access to a
working version of `gw_data_find` without explicitly pointing it to the server
(i.e., that you are working on one of the LDG clusters).


.. |pipeline status| image:: https://git.ligo.org/lscsoft/bilby_pipe/badges/master/pipeline.svg
   :target: https://git.ligo.org/lscsoft/bilby_pipe/commits/master
.. |coverage report| image:: https://lscsoft.docs.ligo.org/bilby_pipe/coverage_badge.svg
   :target: https://lscsoft.docs.ligo.org/bilby_pipe/htmlcov/

