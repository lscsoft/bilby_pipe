=========================
Customising data analysis
=========================

It is possible to specify alternative likelihoods, prior dictionaries, and source models through the ini file.
Each of these are done by passing a full :code:`python` path, for example, to use a :code:`WaveformGenerator` class
and source model from some external package the following should be included in the ini file.

.. code-block:: text

    waveform-generator-class = my_package.submodule.CustomWaveformGenerator
    frequency-domain-source-model = my_package.submodule.custom_source_model

In order to be compatible with the :code:`bilby_pipe` analysis scripts, custom classes should take the same arguments
as their parent classes.
An exception to this is when passing custom likelihood classes.
In this case additional keyword arguments can be passed through the ini file, as below

.. code-block:: text

    likelihood-type = my_package.submodule.CustomLikelihood
    extra-likelihood-kwargs = {new_argument: value, other_argument: other_value}
