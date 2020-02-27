==========
Injections
==========

:code:`bilby_pipe`

Injection files
---------------
The most straight-forward way of defining a set of injections is to provide an
:code:`injection-file=` line in your ini. This should point to either a :code:`dat`
(essentially a CSV file containing rows of injections and columns of parameter
names) or :code:`json` injection file.

Generating injection files
---------------------------
To generate an injection file, we provide the command-line utility
:code:`bilby_pipe_create_injections`. This generates either :code:`dat` or
:code:`json` style injection files by drawing from a bilby prior file. The
prior need not be the same prior used for analysis. As an example, this file
specifies a prior for precessing black hole binary systems

.. code-block:: console

   mass_1 = Uniform(name='mass_1', minimum=10, maximum=80)
   mass_2 = Uniform(name='mass_2', minimum=10, maximum=80)
   mass_ratio =  Constraint(name='mass_ratio', minimum=0.125, maximum=1)
   a_1 = Uniform(name='a_1', minimum=0, maximum=0.99)
   a_2 = Uniform(name='a_2', minimum=0, maximum=0.99)
   tilt_1 = Sine(name='tilt_1')
   tilt_2 = Sine(name='tilt_2')
   phi_12 = Uniform(name='phi_12', minimum=0, maximum=2 * np.pi)
   phi_jl = Uniform(name='phi_jl', minimum=0, maximum=2 * np.pi)
   luminosity_distance = PowerLaw(alpha=2, name='luminosity_distance', minimum=50, maximum=2000)
   dec = Cosine(name='dec')
   ra = Uniform(name='ra', minimum=0, maximum=2 * np.pi)
   theta_jn = Sine(name='theta_jn')
   psi =  Uniform(name='psi', minimum=0, maximum=np.pi)
   phase =  Uniform(name='phase', minimum=0, maximum=2 * np.pi)

Naming this file :code:`bbh.prior` and running

.. code-block:: console

   $ bilby_pipe_create_injection_file bbh.prior --n-injection 100 --generation-seed 1234 -f injections.json

Will produce a file :code:`injections.json` containing 100 random draws from the prior. For a complete list of options, see

.. code-block:: console

   $ bilby_pipe_create_injection_file --help

General tips
------------

No injection file
=================
If :code:`injection-file` is not given in the configuration, but
`injection=True`, then a set of injections will be generated from the
:code:`prior-file` (using :code:bilby_pipe_create_injection_file`).

Interaction with :code:`n-simulation`
=====================================
If :code:`n-simulation` and :code:`injection-file` ar
of injections needs to match :code:`n-simulation`. In this case, coloured
Gaussian noise is simulated used the power-spectal-density (psd) defined in
:code:`psd-dict` or the default aLIGO psd. Then, the injections are simulated
and injected into this noise.

Interaction with :code:`gps-times` or :code:`gps-tuple`
=======================================================
If either :code:`gps-times` or :code:gps-tuple` are given with
:code:`injection-file` or :code:`injection=True` then injections are added to
the inteferometer data. Again, the number of injections needs to match the number
of gps times.

Specifying a subset of injections
=================================
A subset of injections can be selected using the :code:`injection-numbers`
argument. Note, the size of this restricted set must then match either the number
of simulations or the number of gps-times.

Specifying the injection waveform
=================================
A different waveform argument can be given via the :code:`injection-waveform-approximant` option.

XML files
=========
XML files were a common standard for gravitational wave data analysis. We do
not support them natively (as an input file to bilby_pipe), but we provide a
conversion mechanism. For help with this, see

.. code-block:: console

   $ bilby_pipe_xml_converter --help
