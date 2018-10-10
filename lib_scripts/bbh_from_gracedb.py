#!/usr/bin/env python
"""
A Script for running PE based on a gracedb ID
"""
from __future__ import division, print_function

from bilby_pipe import script_helper
import bilby


class GracedbScriptInputs(script_helper.ScriptInput):
    @property
    def gracedb(self):
        return self._gracedb

    @gracedb.setter
    def gracedb(self, gracedb):
        self.candidate, self.frame_caches = bilby.gw.utils.get_gracedb(
            gracedb, self.outdir, self.duration, self.calibration,
            self.detectors)
        self.trigger_time = self.candidate['gpstime']

    @property
    def frequency_domain_source_model(self):
        return bilby.gw.source.lal_binary_black_hole


parser = script_helper.create_default_parser()
parser.add('--gracedb', type=str, help='Gracedb UID', required=True)
args = parser.parse_args()

inputs = GracedbScriptInputs(args)

result = bilby.run_sampler(
    likelihood=inputs.likelihood, priors=inputs.priors, sampler=inputs.sampler,
    label=inputs.run_label, outdir=inputs.outdir,
    # conversion_function=bilby.gw.conversion.generate_all_bbh_parameters,
    **inputs.sampler_kwargs)

result.plot_corner()
