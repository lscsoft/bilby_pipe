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
        """ The gracedb of the candidate """
        return self._gracedb

    @gracedb.setter
    def gracedb(self, gracedb):
        """ Given the gracedb of a candidate, load the data and frame cache """
        self.candidate, self.frame_caches = bilby.gw.utils.get_gracedb(
            gracedb, self.outdir, self.duration, self.calibration,
            self.detectors)
        self._gracedb = gracedb
        self.trigger_time = self.candidate['gpstime']

    @property
    def interferometers(self):
        """ A bilby InterferometerList of interferometers with data """
        try:
            return self._interferometers
        except AttributeError:
            interferometers = bilby.gw.detector.InterferometerList([])
            if self.frame_caches is not None:
                if self.channel_names is None:
                    self.channel_names = [None] * len(self.frame_caches)
                for cache_file, channel_name in zip(self.frame_caches,
                                                    self.channel_names):
                    interferometers.append(
                        bilby.gw.detector.load_data_from_cache_file(
                            cache_file, self.trigger_time, self.duration,
                            self.psd_duration, channel_name))
                self._interferometers = interferometers
                return self._interferometers
            else:
                raise ValueError(
                    "Unable to load data as frame-cache not given")

    @property
    def frequency_domain_source_model(self):
        return bilby.gw.source.lal_binary_black_hole


parser = script_helper.create_default_parser()
parser.add('--gracedb', type=str, help='Gracedb UID', required=True)

inputs = GracedbScriptInputs(parser)

result = bilby.run_sampler(
    likelihood=inputs.likelihood, priors=inputs.priors, sampler=inputs.sampler,
    label=inputs.run_label, outdir=inputs.outdir,
    # conversion_function=bilby.gw.conversion.generate_all_bbh_parameters,
    **inputs.sampler_kwargs)

result.plot_corner()
