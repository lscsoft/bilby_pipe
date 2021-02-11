import argparse
import os
import sys

import configargparse

import bilby
from bilby_pipe.bilbyargparser import BilbyArgParser

from .main import __doc__ as usage
from .utils import get_version_information, logger, nonefloat, noneint, nonestr

__version__ = get_version_information()


class StoreBoolean(argparse.Action):
    """argparse class for robust handling of booleans with configargparse

    When using configargparse, if the argument is setup with
    action="store_true", but the default is set to True, then there is no way,
    in the config file to switch the parameter off. To resolve this, this class
    handles the boolean properly.

    """

    def __call__(self, parser, namespace, value, option_string=None):
        value = str(value).lower()
        if value in ["true"]:
            setattr(namespace, self.dest, True)
        else:
            setattr(namespace, self.dest, False)


def create_parser(top_level=True):
    """Creates the BilbyArgParser for bilby_pipe

    Parameters
    ----------
    top_level:
        If true, parser is to be used at the top-level with requirement
        checking etc, else it is an internal call and will be ignored.

    Returns
    -------
    parser: BilbyArgParser instance
        Argument parser

    """

    parser = BilbyArgParser(
        usage=usage,
        ignore_unknown_config_file_keys=False,
        allow_abbrev=False,
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add("ini", type=str, is_config_file=True, help="Configuration ini file")
    parser.add("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add(
        "--version",
        action="version",
        version=f"%(prog)s={__version__}\nbilby={bilby.__version__}",
    )

    calibration_parser = parser.add_argument_group(
        "Calibration arguments",
        description="Which calibration model and settings to use.",
    )
    calibration_parser.add(
        "--calibration-model",
        type=nonestr,
        default=None,
        choices=["CubicSpline", None],
        help="Choice of calibration model, if None, no calibration is used",
    )

    calibration_parser.add(
        "--spline-calibration-envelope-dict",
        type=nonestr,
        default=None,
        help=("Dictionary pointing to the spline calibration envelope files"),
    )

    calibration_parser.add(
        "--spline-calibration-nodes",
        type=int,
        default=5,
        help=("Number of calibration nodes"),
    )

    calibration_parser.add(
        "--spline-calibration-amplitude-uncertainty-dict",
        type=nonestr,
        default=None,
        help=(
            "Dictionary of the amplitude uncertainties for the constant "
            "uncertainty model"
        ),
    )

    calibration_parser.add(
        "--spline-calibration-phase-uncertainty-dict",
        type=nonestr,
        default=None,
        help=(
            "Dictionary of the phase uncertainties for the constant "
            "uncertainty model"
        ),
    )

    if top_level is False:
        parser.add("--idx", type=int, help="The level A job index", default=0)
        parser.add(
            "--data-dump-file",
            type=nonestr,
            default=None,
            help="Filename for the data dump: only used internally by data_analysis",
        )

    data_gen_pars = parser.add_argument_group(
        "Data generation arguments",
        description="How to generate the data, e.g., from a list of gps times or simulated Gaussian noise.",
    )

    data_gen_pars.add(
        "--ignore-gwpy-data-quality-check",
        action=StoreBoolean,
        default=True,
        help=(
            "Ignores the check to see if data queried from GWpy (ie not gaussian "
            "noise) is obtained from time when the IFOs are in science mode."
        ),
    )

    data_gen_pars.add(
        "--gps-tuple",
        type=nonestr,
        help=(
            "Tuple of the (start, step, number) of GPS start times. For"
            " example, (10, 1, 3) produces the gps start times [10, 11, 12]."
            " If given, gps-file is ignored."
        ),
        default=None,
    )
    data_gen_pars.add(
        "--gps-file",
        type=nonestr,
        help=(
            "File containing segment GPS start times. This can be a multi-"
            "column file if (a) it is comma-separated and (b) the zeroth "
            "column contains the gps-times to use"
        ),
        default=None,
    )
    data_gen_pars.add(
        "--timeslide-file",
        type=nonestr,
        help=(
            "File containing detector timeslides. "
            "Requires a GPS time file to also be provided. One column for each "
            "detector. Order of detectors specified by `--detectors` argument. "
            "Number of timeslides must correspond to the number of GPS times provided."
        ),
        default=None,
    )
    data_gen_pars.add(
        "--timeslide-dict",
        type=nonestr,
        help=(
            "Dictionary containing detector timeslides: applies a fixed offset"
            " per detector. E.g. to apply +1s in H1, {H1: 1}"
        ),
        default=None,
    )
    data_gen_pars.add(
        "--trigger-time",
        default=None,
        type=nonestr,
        help=(
            "Either a GPS trigger time, or the event name (e.g. GW150914). "
            "For event names, the gwosc package is used to identify the "
            "trigger time"
        ),
    )
    data_gen_pars.add(
        "--n-simulation",
        type=int,
        default=0,
        help=(
            "Number of simulated segments to use with gaussian-noise "
            "Note, this must match the number of injections specified"
        ),
    )
    data_gen_pars.add(
        "--data-dict",
        default=None,
        type=nonestr,
        help="Dictionary of paths to gwf, or hdf5 data files",
    )
    data_gen_pars.add(
        "--data-format",
        default=None,
        type=nonestr,
        help=(
            "If given, the data format to pass to "
            " `gwpy.timeseries.TimeSeries.read(), see "
            " gwpy.github.io/docs/stable/timeseries/io.html"
        ),
    )
    data_gen_pars.add(
        "--allow-tape",
        default=True,
        action=StoreBoolean,
        help=(
            "If true (default), allow reading data from tape."
            " See `gwpy.timeseries.TimeSeries.get() for more information."
        ),
    )
    data_gen_pars.add(
        "--channel-dict",
        type=nonestr,
        default=None,
        help=(
            "Channel dictionary: keys relate to the detector with values "
            "the channel name, e.g. 'GDS-CALIB_STRAIN'. For GWOSC open data, "
            "set the channel-dict keys to 'GWOSC'. Note, the "
            "dictionary should follow basic python dict syntax."
        ),
    )
    data_type_pars = data_gen_pars.add_mutually_exclusive_group()
    data_type_pars.add(
        "--gaussian-noise",
        action="store_true",
        help="If true, use simulated Gaussian noise",
    )
    data_type_pars.add(
        "--zero-noise",
        action="store_true",
        help="Use a zero noise realisation",
    )

    det_parser = parser.add_argument_group(
        title="Detector arguments",
        description="How to set up the interferometers and power spectral density.",
    )
    det_parser.add(
        "--coherence-test",
        action="store_true",
        help=(
            "Run the analysis for all detectors together and for each "
            "detector separately"
        ),
    )
    det_parser.add(
        "--detectors",
        action="append",
        help=(
            "The names of detectors to use. If given in the ini file, "
            "detectors are specified by `detectors=[H1, L1]`. If given "
            "at the command line, as `--detectors H1 --detectors L1`"
        ),
    )
    det_parser.add(
        "--duration",
        type=float,
        default=4,
        help="The duration of data around the event to use",
    )
    det_parser.add(
        "--generation-seed",
        default=None,
        type=noneint,
        help=(
            "Random seed used during data generation. If no generation seed "
            "provided, a random seed between 1 and 1e6 is selected. If a seed "
            "is provided, it is used as the base seed and all generation jobs "
            "will have their seeds set as {generation_seed = base_seed + job_idx}."
        ),
    )
    det_parser.add(
        "--psd-dict", type=nonestr, default=None, help="Dictionary of PSD files to use"
    )
    det_parser.add(
        "--psd-fractional-overlap",
        default=0.5,
        type=float,
        help="Fractional overlap of segments used in estimating the PSD",
    )
    det_parser.add(
        "--post-trigger-duration",
        type=float,
        default=2.0,
        help=("Time (in s) after the trigger_time to the end of the segment"),
    )
    det_parser.add("--sampling-frequency", default=4096, type=float)

    det_parser.add(
        "--psd-length",
        default=32,
        type=int,
        help=(
            "Sets the psd duration (up to the psd-duration-maximum). PSD "
            "duration calculated by psd-length x duration [s]. Default is 32."
        ),
    )
    det_parser.add(
        "--psd-maximum-duration",
        default=1024,
        type=int,
        help=("The maximum allowed PSD duration in seconds, default is 1024s."),
    )
    det_parser.add(
        "--psd-method",
        default="median",
        type=str,
        help="PSD method see gwpy.timeseries.TimeSeries.psd for options",
    )
    det_parser.add(
        "--psd-start-time",
        default=None,
        type=nonefloat,
        help=(
            "Start time of data (relative to the segment start) used to "
            " generate the PSD. Defaults to psd-duration before the"
            " segment start time"
        ),
    )
    det_parser.add(
        "--maximum-frequency",
        default=None,
        type=nonestr,
        help=(
            "The maximum frequency, given either as a float for all detectors "
            "or as a dictionary (see minimum-frequency)"
        ),
    )
    det_parser.add(
        "--minimum-frequency",
        default="20",
        type=str,
        help=(
            "The minimum frequency, given either as a float for all detectors "
            "or as a dictionary where all keys relate the detector with values"
            " of the minimum frequency, e.g. {H1: 10, L1: 20}. If the waveform"
            " generation should start the minimum frequency for any of the "
            "detectors, add another entry to the dictionary, e.g., "
            "{H1: 40, L1: 60, waveform: 20}."
        ),
    )
    det_parser.add(
        "--tukey-roll-off",
        default=0.4,
        type=float,
        help="Roll off duration of tukey window in seconds, default is 0.4s",
    )
    det_parser.add(
        "--resampling-method",
        default="lal",
        type=str,
        choices=["lal", "gwpy"],
        help="Resampling method to use: lal matches the resampling used by lalinference/BayesWave",
    )

    injection_parser = parser.add_argument_group(
        title="Injection arguments",
        description="Whether to include software injections and how to generate them.",
    )
    injection_parser.add(
        "--injection",
        action="store_true",
        default=False,
        help="Create data from an injection file",
    )
    injection_parser_input = injection_parser.add_mutually_exclusive_group()
    injection_parser_input.add(
        "--injection-dict",
        type=nonestr,
        default=None,
        help="A single injection dictionary given in the ini file",
    )
    injection_parser_input.add(
        "--injection-file",
        type=nonestr,
        default=None,
        help=(
            "Injection file to use. See `bilby_pipe_create_injection_file --help`"
            " for supported formats"
        ),
    )
    injection_parser.add(
        "--injection-numbers",
        action="append",
        default=None,
        help=(
            "Specific injections rows to use from the injection_file, e.g. "
            "`injection_numbers=[0,3] selects the zeroth and third row"
        ),
    )
    injection_parser.add(
        "--injection-waveform-approximant",
        type=nonestr,
        default=None,
        help="The name of the waveform approximant to use to create injections. "
        "If none is specified, then the `waveform-approximant` will be used"
        "as the `injection-waveform-approximant`.",
    )

    submission_parser = parser.add_argument_group(
        title="Job submission arguments",
        description="How the jobs should be formatted, e.g., which job scheduler to use.",
    )
    submission_parser.add(
        "--accounting",
        type=nonestr,
        help="Accounting group to use (see, https://accounting.ligo.org/user)",
    )
    submission_parser.add("--label", type=str, default="label", help="Output label")
    submission_parser.add(
        "--local",
        action="store_true",
        help="Run the job locally, i.e., not through a batch submission",
    )
    submission_parser.add(
        "--local-generation",
        action="store_true",
        help=(
            "Run the data generation job locally. This may be useful for "
            "running on a cluster where the compute nodes do not have "
            "internet access. For HTCondor, this is done using the local "
            "universe, for slurm, the jobs will be run at run-time"
        ),
    )
    submission_parser.add(
        "--local-plot", action="store_true", help="Run the plot job locally"
    )

    submission_parser.add(
        "--outdir",
        type=str,
        default="outdir",
        help="The output directory. If outdir already exists, an auto-incrementing naming scheme is used",
    )
    submission_parser.add(
        "--overwrite-outdir",
        action="store_true",
        help="If given, overwrite the outdir (if it exists)",
    )
    submission_parser.add(
        "--periodic-restart-time",
        default=28800,
        type=int,
        help=(
            "Time after which the job will self-evict when scheduler=condor."
            " After this, condor will restart the job. Default is 28800."
            " This is used to decrease the chance of HTCondor hard evictions"
        ),
    )
    submission_parser.add(
        "--request-memory",
        type=float,
        default=4.0,
        help="Memory allocation request (GB), defaults is 4GB",
    )
    submission_parser.add(
        "--request-memory-generation",
        type=nonefloat,
        default=None,
        help="Memory allocation request (GB) for data generation step",
    )
    submission_parser.add(
        "--request-cpus",
        type=int,
        default=1,
        help="Use multi-processing (for available samplers: dynesty, ptemcee, cpnest)",
    )
    submission_parser.add(
        "--singularity-image",
        type=nonestr,
        default=None,
        help="Singularity image to use",
    )
    submission_parser.add(
        "--scheduler",
        type=str,
        default="condor",
        help="Format submission script for specified scheduler. Currently implemented: SLURM",
    )
    submission_parser.add(
        "--scheduler-args",
        type=nonestr,
        default=None,
        help=(
            "Space-separated #SBATCH command line args to pass to slurm. "
            "The args needed will depend on the setup of your slurm scheduler."
            "Please consult documentation for your local cluster (slurm only)."
        ),
    )
    submission_parser.add(
        "--scheduler-module",
        type=nonestr,
        action="append",
        default=None,
        help="Space-separated list of modules to load at runtime (slurm only)",
    )
    submission_parser.add(
        "--scheduler-env",
        type=nonestr,
        default=None,
        help="Python environment to activate (slurm only)",
    )
    submission_parser.add(
        "--scheduler-analysis-time", type=nonestr, default="7-00:00:00", help=""
    )
    submission_parser.add(
        "--submit",
        action="store_true",
        help="Attempt to submit the job after the build",
    )
    submission_parser.add(
        "--condor-job-priority",
        type=int,
        default=0,
        help=(
            "Job priorities allow a user to sort their HTCondor jobs to determine "
            "which are tried to be run first. "
            "A job priority can be any integer: larger values denote better priority. "
            "By default HTCondor job priority=0. "
        ),
    )
    submission_parser.add(
        "--transfer-files",
        action=StoreBoolean,
        default=True,
        help=(
            "If true, use HTCondor file transfer mechanism, default is True"
            "for non-condor schedulers, this option is ignored"
        ),
    )
    submission_parser.add(
        "--log-directory",
        type=nonestr,
        default=None,
        help="If given, an alternative path for the log output",
    )
    submission_parser.add(
        "--online-pe", action="store_true", help="Flag for online PE settings"
    )
    submission_parser.add(
        "--osg",
        action="store_true",
        default=False,
        help="If true, format condor submission for running on OSG, default is False",
    )
    submission_parser.add(
        "--analysis-executable",
        default=None,
        type=nonestr,
        help=(
            "Path to an executable to replace bilby_pipe_analysis, be aware"
            " that this executable will pass the complete ini file (in the"
            " outdir.)"
        ),
    )

    likelihood_parser = parser.add_argument_group(
        title="Likelihood arguments",
        description="Options for setting up the likelihood.",
    )
    likelihood_parser.add(
        "--distance-marginalization",
        action="store_true",
        default=False,
        help="Boolean. If true, use a distance-marginalized likelihood",
    )
    likelihood_parser.add(
        "--distance-marginalization-lookup-table",
        default=None,
        type=nonestr,
        help="Path to the distance-marginalization lookup table",
    )

    likelihood_parser.add(
        "--phase-marginalization",
        action="store_true",
        default=False,
        help="Boolean. If true, use a phase-marginalized likelihood",
    )
    likelihood_parser.add(
        "--time-marginalization",
        action="store_true",
        default=False,
        help="Boolean. If true, use a time-marginalized likelihood",
    )
    likelihood_parser.add(
        "--jitter-time",
        action=StoreBoolean,
        default=True,
        help="Boolean. If true, and using a time-marginalized likelihood 'time jittering' will be performed",
    )
    likelihood_parser.add(
        "--reference-frame",
        default="sky",
        type=str,
        help="Reference frame for the sky parameterisation, either 'sky' (default) or, e.g., 'H1L1'",
    )
    likelihood_parser.add(
        "--time-reference",
        default="geocent",
        type=str,
        help="Time parameter to sample in, either 'geocent' (default) or, e.g., 'H1'",
    )
    likelihood_parser.add(
        "--likelihood-type",
        default="GravitationalWaveTransient",
        help=(
            "The likelihood. Can be one of [GravitationalWaveTransient, "
            "ROQGravitationalWaveTransient] or python path to a bilby "
            "likelihood class available in the users installation. "
            "Need to specify --roq-folder if ROQ likelihood used"
        ),
    )
    likelihood_parser.add(
        "--roq-folder", type=nonestr, default=None, help="The data for ROQ"
    )
    likelihood_parser.add(
        "--roq-weights",
        type=nonestr,
        default=None,
        help=(
            "If given, the ROQ weights to use (rather than building them). "
            "This must be given along with the roq-folder for checking"
        ),
    )
    likelihood_parser.add(
        "--roq-scale-factor",
        default=1,
        type=float,
        help="Rescaling factor for the ROQ, default is 1 (no rescaling)",
    )
    likelihood_parser.add(
        "--extra-likelihood-kwargs",
        type=nonestr,
        default=None,
        help="Additional keyword arguments to pass to the likelihood. Any arguments "
        "which are named bilby_pipe arguments, e.g., distance_marginalization "
        "should NOT be included. This is only used if you are not using the "
        "GravitationalWaveTransient or ROQGravitationalWaveTransient likelihoods",
    )

    output_parser = parser.add_argument_group(
        title="Output arguments", description="What kind of output/summary to generate."
    )
    output_parser.add(
        "--create-plots",
        action="store_true",
        help="Create diagnostic and posterior plots",
    )
    output_parser.add_argument(
        "--plot-calibration",
        action="store_true",
        help="Create calibration posterior plot",
    )
    output_parser.add_argument(
        "--plot-corner",
        action="store_true",
        help="Create intrinsic and extrinsic posterior corner plots",
    )
    output_parser.add_argument(
        "--plot-marginal",
        action="store_true",
        help="Create 1-d marginal posterior plots",
    )
    output_parser.add_argument(
        "--plot-skymap", action="store_true", help="Create posterior skymap"
    )
    output_parser.add_argument(
        "--plot-waveform", action="store_true", help="Create waveform posterior plot"
    )
    output_parser.add_argument(
        "--plot-format",
        default="png",
        help="Format for making bilby_pipe plots, can be [png, pdf, html]. "
        "If specified format is not supported, will default to png.",
    )

    output_parser.add(
        "--create-summary", action="store_true", help="Create a PESummary page"
    )
    output_parser.add("--email", type=nonestr, help="Email for notifications")
    output_parser.add(
        "--notification",
        type=nonestr,
        default="Never",
        help=(
            "Notification setting for HTCondor jobs. "
            "One of 'Always','Complete','Error','Never'. "
            "If defined by 'Always', "
            "the owner will be notified whenever the job "
            "produces a checkpoint, as well as when the job completes. "
            "If defined by 'Complete', "
            "the owner will be notified when the job terminates. "
            "If defined by 'Error', "
            "the owner will only be notified if the job terminates abnormally, "
            "or if the job is placed on hold because of a failure, "
            "and not by user request. "
            "If defined by 'Never' (the default), "
            "the owner will not receive e-mail, regardless to what happens to the job. "
            "Note, an `email` arg is also required for notifications to be emailed. "
        ),
    )
    output_parser.add(
        "--existing-dir",
        type=nonestr,
        default=None,
        help=(
            "If given, add results to an directory with an an existing"
            " summary.html file"
        ),
    )
    output_parser.add(
        "--webdir",
        type=nonestr,
        default=None,
        help=(
            "Directory to store summary pages. If not given, defaults to "
            "outdir/results_page"
        ),
    )
    output_parser.add(
        "--summarypages-arguments",
        type=nonestr,
        default=None,
        help="Arguments (in the form of a dictionary) to pass to the summarypages executable",
    )

    prior_parser = parser.add_argument_group(
        title="Prior arguments", description="Specify the prior settings."
    )
    prior_parser.add(
        "--default-prior",
        default="BBHPriorDict",
        type=str,
        help="The name of the prior set to base the prior on. Can be one of"
        "[PriorDict, BBHPriorDict, BNSPriorDict, CalibrationPriorDict]",
    )
    prior_parser.add(
        "--deltaT",
        type=float,
        default=0.2,
        help=(
            "The symmetric width (in s) around the trigger time to"
            " search over the coalesence time"
        ),
    )
    prior_parser_main = prior_parser.add_mutually_exclusive_group()
    prior_parser_main.add(
        "--prior-file", type=nonestr, default=None, help="The prior file"
    )
    prior_parser_main.add(
        "--prior-dict",
        type=nonestr,
        default=None,
        help=(
            "A dictionary of priors (alternative to prior-file). Multiline "
            "dictionaries are supported, but each line must contain a single"
            "parameter specification and finish with a comma."
        ),
    )
    prior_parser.add(
        "--convert-to-flat-in-component-mass",
        action=StoreBoolean,
        default=False,
        help=(
            "Convert a flat-in chirp mass and mass-ratio prior file to flat "
            "in component mass during the post-processing. Note, the prior "
            "must be uniform in Mc and q with constraints in m1 and m2 for "
            "this to work"
        ),
    )

    postprocessing_parser = parser.add_argument_group(
        title="Post processing arguments",
        description="What post-processing to perform.",
    )
    postprocessing_parser.add(
        "--postprocessing-executable",
        type=nonestr,
        default=None,
        help=(
            "An executable name for postprocessing. A single postprocessing "
            " job is run as a child of all analysis jobs"
        ),
    )
    postprocessing_parser.add(
        "--postprocessing-arguments",
        type=nonestr,
        default=None,
        help="Arguments to pass to the postprocessing executable",
    )
    postprocessing_parser.add(
        "--single-postprocessing-executable",
        type=nonestr,
        default=None,
        help=(
            "An executable name for postprocessing. A single postprocessing "
            "job is run as a child for each analysis jobs: note the "
            "difference with respect postprocessing-executable"
        ),
    )
    postprocessing_parser.add(
        "--single-postprocessing-arguments",
        type=nonestr,
        default=None,
        help=(
            "Arguments to pass to the single postprocessing executable. The "
            "str '$RESULT' will be replaced by the path to the individual "
            "result file"
        ),
    )

    sampler_parser = parser.add_argument_group(title="Sampler arguments")
    sampler_parser.add("--sampler", type=str, default="dynesty", help="Sampler to use")
    sampler_parser.add(
        "--sampling-seed", default=None, type=noneint, help="Random sampling seed"
    )
    sampler_parser.add(
        "--n-parallel",
        type=int,
        default=1,
        help="Number of identical parallel jobs to run per event",
    )
    sampler_parser.add(
        "--sampler-kwargs",
        type=str,
        default="Default",
        help=(
            "Dictionary of sampler-kwargs to pass in, e.g., {nlive: 1000} OR "
            "pass pre-defined set of sampler-kwargs {Default, FastTest}"
        ),
    )

    # Waveform arguments
    waveform_parser = parser.add_argument_group(
        title="Waveform arguments", description="Setting for the waveform generator"
    )
    waveform_parser.add(
        "--waveform-generator",
        default="bilby.gw.waveform_generator.WaveformGenerator",
        type=str,
        help="The waveform generator class, should be a python path. This will "
        "not be able to use any arguments not passed to the default.",
    )
    waveform_parser.add(
        "--reference-frequency", default=20, type=float, help="The reference frequency"
    )
    waveform_parser.add(
        "--waveform-approximant",
        default="IMRPhenomPv2",
        type=str,
        help="The name of the waveform approximant to use for PE.",
    )
    waveform_parser.add(
        "--catch-waveform-errors",
        default=False,
        action=StoreBoolean,
        help="Turns on waveform error catching",
    )
    waveform_parser.add(
        "--pn-spin-order",
        default=-1,
        type=int,
        help="Post-newtonian order to use for the spin",
    )
    waveform_parser.add(
        "--pn-tidal-order",
        default=-1,
        type=int,
        help="Post-Newtonian order to use for tides",
    )
    waveform_parser.add(
        "--pn-phase-order",
        default=-1,
        type=int,
        help="post-Newtonian order to use for the phase",
    )
    waveform_parser.add(
        "--pn-amplitude-order",
        default=0,
        type=int,
        help="Post-Newtonian order to use for the amplitude. Also "
        "used to determine the waveform starting frequency.",
    )
    waveform_parser.add(
        "--numerical-relativity-file",
        default=None,
        type=nonestr,
        help=(
            "Path to a h5 numerical relativity file to inject, see"
            "https://git.ligo.org/waveforms/lvcnr-lfs for examples"
        ),
    )
    waveform_parser.add(
        "--waveform-arguments-dict",
        default=None,
        type=nonestr,
        help=(
            "A dictionary of arbitrary additional waveform-arguments to pass"
            "  to the bilby waveform generator's `waveform_arguments`"
        ),
    )
    waveform_parser.add(
        "--mode-array",
        default=None,
        type=nonestr,
        action="append",
        help="Array of modes to use for the waveform. Should be "
        "a list of lists, eg. [[2,2], [2,-2]]",
    )
    waveform_parser.add(
        "--frequency-domain-source-model",
        default="lal_binary_black_hole",
        type=str,
        help=(
            "Name of the frequency domain source model. Can be one of"
            "[lal_binary_black_hole, lal_binary_neutron_star,"
            "lal_eccentric_binary_black_hole_no_spins, sinegaussian, "
            "supernova, supernova_pca_model] or any python  path to a bilby "
            " source function the users installation, e.g. examp.source.bbh"
        ),
    )
    waveform_parser.add(
        "--conversion-function",
        default=None,
        type=nonestr,
        help=(
            "Optional python path to a user-specified conversion function "
            "If unspecified, this is determined by the frequency_domain_source_model."
            "If the source-model contains binary_black_hole, "
            "the conversion function is bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters. "
            "If the source-model contains binary_neutron_star, "
            "the generation function is bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters. "
            "If you specify your own function, you may wish to use the I/O of those functions as templates"
        ),
    )
    waveform_parser.add(
        "--generation-function",
        default=None,
        type=nonestr,
        help=(
            "Optional python path to a user-specified generation function "
            "If unspecified, this is determined by the frequency_domain_source_model."
            "If the source-model contains binary_black_hole, "
            "the generation function is bilby.gw.conversion.generate_all_bbh_parameters. "
            "If the source-model contains binary_neutron_star, "
            "the generation function is bilby.gw.conversion.generate_all_bns_parameters. "
            "If you specify your own function, you may wish to use the I/O of those functions as templates"
        ),
    )

    return parser


def main():
    filename = sys.argv[1]
    if filename in ["-h", "--help"]:
        logger.info("Write a default config.ini file to the specified filename.")
        logger.info("Example usage: $ bilby_pipe_write_default_ini config.ini")
        sys.exit()
    else:
        parser = create_parser()
        logger.info(f"Default config file written to {os.path.abspath(filename)}")
        parser.write_to_file(
            filename=filename, overwrite=True, include_description=True
        )
