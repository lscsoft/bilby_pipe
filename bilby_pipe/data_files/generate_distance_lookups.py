import glob
import os
import sys

import matplotlib.pyplot as plt
from numpy import linspace

import bilby
from bilby_pipe.utils import DURATION_LOOKUPS

# fmt: off
import matplotlib  # isort:skip
matplotlib.use("agg")
# fmt: on


def plot_SNRs(ax, label, prior, waveform_generator, n_samples=200):
    optimal_snr = []

    for _ in range(n_samples):
        H1 = bilby.gw.detector.get_empty_interferometer("H1")
        H1.set_strain_data_from_power_spectral_density(
            sampling_frequency=waveform_generator.sampling_frequency,
            duration=waveform_generator.duration,
            start_time=0,
        )
        parameters = priors.sample()
        parameters["geocent_time"] = 0
        H1.inject_signal(waveform_generator=waveform_generator, parameters=parameters)
        optimal_snr.append(H1.meta_data["optimal_SNR"])

    ax.hist(optimal_snr, bins=linspace(0, 50, 50), label=label, density=True)
    ax.set_yticklabels([])
    ax.legend()


ifos = [bilby.gw.detector.get_empty_interferometer("H1")]
waveform_arguments = dict(waveform_approximant="IMRPhenomPv2", reference_frequency=50.0)

filenames = glob.glob("*prior")
if "plot" in sys.argv:
    snr_fig, snr_axes = plt.subplots(nrows=len(filenames), sharex=True, figsize=(5, 9))

for ii, filename in enumerate(filenames):
    duration = DURATION_LOOKUPS[filename.rstrip(".prior")]
    waveform_generator = bilby.gw.WaveformGenerator(
        sampling_frequency=8192,
        duration=duration,
        frequency_domain_source_model=bilby.gw.source.lal_binary_black_hole,
        parameter_conversion=bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters,
        waveform_arguments=waveform_arguments,
    )

    print("Generating lookup table for prior-file {}".format(filename))
    dest = "{}_distance_marginalization_lookup.npz".format(
        os.path.splitext(filename)[0]
    )
    priors = bilby.gw.prior.BBHPriorDict(filename)

    if "plot" in sys.argv:
        plot_SNRs(snr_axes[ii], filename, priors, waveform_generator)

    bilby.gw.likelihood.GravitationalWaveTransient(
        ifos,
        waveform_generator,
        distance_marginalization=True,
        time_marginalization=False,
        phase_marginalization=True,
        priors=priors,
        distance_marginalization_lookup_table=dest,
    )


if "plot" in sys.argv:
    snr_axes[-1].set_xlabel("optimal SNR")
    snr_fig.tight_layout()
    snr_fig.savefig("SNR_distributions.png")
