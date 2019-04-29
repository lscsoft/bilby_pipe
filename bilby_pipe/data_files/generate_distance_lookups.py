import glob
import os

import bilby

ifos = [bilby.gw.detector.get_empty_interferometer("H1")]
wfg = bilby.gw.waveform_generator.WaveformGenerator(
    frequency_domain_source_model=bilby.gw.source.lal_binary_black_hole
)

for filename in glob.glob("*prior"):
    print("Generating lookup table for prior-file {}".format(filename))
    dest = "{}_distance_marginalization_lookup.npz".format(
        os.path.splitext(filename)[0]
    )
    priors = bilby.gw.prior.BBHPriorDict(filename)
    bilby.gw.likelihood.GravitationalWaveTransient(
        ifos,
        wfg,
        distance_marginalization=True,
        priors=priors,
        distance_marginalization_lookup_table=dest,
    )
