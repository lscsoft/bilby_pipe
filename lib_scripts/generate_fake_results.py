#!/usr/bin/env python
"""
A Script for testing the output page creation
"""

from bilby_pipe import script_helper
import bilby
import pandas as pd
import numpy as np

parser = script_helper.create_default_parser()
inputs = script_helper.ScriptInput(parser)

result = bilby.result.Result()
result.outdir = inputs.outdir
result.label = inputs.run_label
result.search_parameter_keys = ['a', 'b']
result.parameter_labels_with_unit = ['a', 'b']
result.posterior = pd.DataFrame(dict(a=np.random.normal(0, 1, 100),
                                     b=np.random.normal(0, 1, 100)))
result.save_to_file()
result.plot_corner()
