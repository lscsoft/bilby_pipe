=====================
The Open Science Grid
=====================

The `Open Science Grid <https://opensciencegrid.org/>`_ (OSG), is an ideal
resource for large-scale non-time-senstive analyses. :code`bilby_pipe` provides
a simple interface to enable jobs to be submitted through the OSG.

To run jobs through the OSG, login to

.. code-block:: console

   ssh albert.einstein@ldas-osg.ligo.caltech.edu

Then submit usual :code:`bilby_pipe` jobs, but with the flat

.. code-block:: console

   osg = True

In your configuration (ini) files.

.. note::
   When running on the OSG, the software you run needs to be available on the compute nodes. This is most easily done by using the `IGWN conda distribution available through cvmfs <https://computing.docs.ligo.org/conda/>`_. We do not support access to arbitrary software installations across the OSG. For testing, you may find it useful to use the:code:`analysis-executable` to point to the cvmfs-installed :code:`bilby_pipe_analysis` executable.
