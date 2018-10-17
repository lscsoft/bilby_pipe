#!/usr/bin/env python
"""
A script for running PE based on a simulated binary black hole signal
"""
from __future__ import division, print_function

from bilby_pipe import script_helper
import bilby


class InjectionScriptInputs(script_helper.ScriptInput):
    @property
    def frequency_domain_source_model(self):
        return bilby.gw.source.lal_binary_black_hole


parser = script_helper.create_default_parser()
inputs = InjectionScriptInputs(parser)

priors = inputs.priors
waveform_generator = inputs.waveform_generator

injection_parameters = priors.sample()
while injection_parameters['mass_1'] < injection_parameters['mass_2']:
    injection_parameters = priors.sample()
ifos = bilby.gw.detector.InterferometerList(inputs.detectors)
ifos.set_strain_data_from_power_spectral_densities(
    sampling_frequency=inputs.sampling_frequency, duration=inputs.duration,
    start_time=inputs.trigger_time - inputs.duration / 2.)
ifos.inject_signal(waveform_generator=waveform_generator,
                   parameters=injection_parameters)
inputs.ifos = ifos

for key in ['a_1', 'a_2', 'tilt_1', 'tilt_2', 'phi_12', 'phi_jl', 'psi', 'ra',
            'dec', 'geocent_time', 'phase']:
    priors[key] = injection_parameters[key]

likelihood = bilby.gw.likelihood.GravitationalWaveTransient(
    interferometers=inputs.ifos, waveform_generator=inputs.waveform_generator,
    prior=priors, phase_marginalization=inputs.phase_marginalization,
    distance_marginalization=inputs.distance_marginalization,
    time_marginalization=inputs.time_marginalization)

result = bilby.run_sampler(
    likelihood=likelihood, priors=priors, sampler=inputs.sampler,
    label=inputs.run_label, outdir=inputs.outdir,
    **inputs.sampler_kwargs)

result.plot_corner()
