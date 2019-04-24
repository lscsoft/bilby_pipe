from bilby_pipe.bilbyargparser import BilbyArgParser
from . import utils

__version__ = utils.get_version_information()


def create_parser(top_level=True):
    """ Creates the BilbyArgParser for bilby_pipe

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

    if top_level is True:
        required = True
    else:
        required = False

    parser = BilbyArgParser(
        usage=__doc__, ignore_unknown_config_file_keys=True, allow_abbrev=False
    )
    parser.add("ini", type=str, is_config_file=True, help="Configuration ini file")
    parser.add("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add(
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )

    calibration_parser = parser.add_argument_group("Calibration arguments")
    calibration_parser.add(
        "--calibration-model",
        type=str,
        default=None,
        choices=["CubicSpline"],
        help="Choice of calibration model, if None, no calibration is used",
    )

    calibration_parser.add(
        "--spline-calibration-envelope-dict",
        type=str,
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
        type=str,
        default=None,
        help=(
            "Dictionary of the amplitude uncertainties for the constant "
            "uncertainty model"
        ),
    )

    calibration_parser.add(
        "--spline-calibration-phase-uncertainty-dict",
        type=str,
        default=None,
        help=(
            "Dictionary of the phase uncertainties for the constant "
            "uncertainty model"
        ),
    )

    if top_level is False:
        parser.add("--idx", type=int, help="The level A job index", default=0)
        parser.add("--cluster", type=str, help="The condor cluster ID", default=None)
        parser.add("--process", type=str, help="The condor process ID", default=None)
        parser.add("--data-label", default=None, help="Label used for the data dump")

    data_gen_pars = parser.add_argument_group("Data generation arguments")
    data_gen_pars.add(
        "--gps-file",
        type=str,
        help="File containing segment GPS start times",
        default=None,
    )
    data_gen_pars.add("--gracedb", type=str, help="Gracedb UID", default=None)
    data_gen_pars.add(
        "--trigger-time",
        default=None,
        type=float,
        help="The trigger time, alternative to --gracedb",
    )

    det_parser = parser.add_argument_group(title="Detector arguments")
    det_parser.add(
        "--channel-dict",
        default=None,
        help=(
            "Channel dictionary: keys relate to the detector with values "
            "the channel name, e.g. 'GDS-CALIB_STRAIN'. Note, the "
            "dictionary should follow basic python dict syntax."
        ),
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
        type=int,
        default=4,
        help="The duration of data around the event to use",
    )
    det_parser.add(
        "--generation-seed",
        default=None,
        type=int,
        help="Random seed used during data generation",
    )
    det_parser.add(
        "--psd-dict", type=str, default=None, help="Dictionary of PSD files to use"
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
        default=2,
        help=("Time (in s) after the trigger_time to the end of the segment"),
    )
    det_parser.add("--sampling-frequency", default=2048, type=int)

    det_parser.add(
        "--psd-length",
        default=32,
        type=int,
        help=("Number of duration-lenths used to generate the PSD, default" " is 32."),
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
        type=float,
        help=(
            "Start time of data (relative to the segment start) used to "
            " generate the PSD. Defaults to psd-duration before the"
            " segment start time"
        ),
    )
    det_parser.add(
        "--maximum-frequency",
        default=None,
        type=str,
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
            " of the minimum frequency, e.g. {H1: 10, L1: 20}."
        ),
    )

    injection_parser = parser.add_argument_group(title="Injection arguments")
    injection_parser.add(
        "--injection",
        action="store_true",
        default=False,
        help="Create data from an injection file",
    )
    injection_parser.add(
        "--injection-file",
        type=str,
        default=None,
        help="Injection file: overrides `n-injection`.",
    )
    injection_parser.add_arg(
        "--n-injection",
        type=int,
        help="Number of injections to generate by sampling from the prior",
    )

    submission_parser = parser.add_argument_group(title="Job submission arguments")
    submission_parser.add(
        "--accounting",
        type=str,
        required=required,
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
            "Run the data generation job locally. Note that if you are "
            "running on a cluster where the compute nodes do not have "
            "internet access, e.g. on ARCCA, you will need to run the "
            "data generation job locally."
        ),
    )
    submission_parser.add("--outdir", type=str, default=".", help="Output directory")
    submission_parser.add(
        "--request-memory",
        type=float,
        default=4,
        help="Memory allocation request (GB), defaults is 4GB",
    )
    submission_parser.add(
        "--request-cpus",
        type=int,
        default=1,
        help="CPU allocation request (required multi-processing jobs)",
    )

    submission_parser.add(
        "--singularity-image", type=str, default=None, help="Singularity image to use"
    )
    submission_parser.add(
        "--submit",
        action="store_true",
        help="Attempt to submit the job after the build",
    )
    submission_parser.add(
        "--transfer-files",
        action="store_true",
        default=False,
        help="If true, use HTCondor file transfer mechanism, default is False",
    )
    submission_parser.add(
        "--X509",
        type=str,
        default=None,
        help=(
            "The path to the users X509 certificate file."
            " Defaults to a copy of the file at the environment variable"
            " $X509_USER_PROXY saved in outdir and linked in"
            " the condor jobs submission"
        ),
    )

    likelihood_parser = parser.add_argument_group(title="Likelihood arguments")
    likelihood_parser.add(
        "--distance-marginalization",
        action="store_true",
        default=False,
        help="Boolean. If true, use a distance-marginalized likelihood",
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
        "--likelihood-type",
        default="GravitationalWaveTransient",
        help="The likelihood. Can be one of"
        "[GravitationalWaveTransient, ROQGravitationalWaveTransient]"
        "Need to specify --roq-folder if ROQ likelihood used",
    )
    likelihood_parser.add("--roq-folder", default=None, help="The data for ROQ")

    output_parser = parser.add_argument_group(title="Output arguments")
    output_parser.add(
        "--create-plots",
        action="store_true",
        help="Create diagnostic and posterior plots",
    )

    output_parser.add(
        "--create-summary", action="store_true", help="Create a PESummary page"
    )
    output_parser.add("--email", type=str, help="Email for notifications")
    output_parser.add(
        "--existing-dir",
        type=str,
        default=None,
        help=(
            "If given, add results to an directory with an an existing"
            " summary.html file"
        ),
    )
    output_parser.add(
        "--webdir",
        type=str,
        default=None,
        help=(
            "Directory to store summary pages. If not given, defaults to "
            "outdir/results_page"
        ),
    )

    prior_parser = parser.add_argument_group(title="Prior arguments")
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
    prior_parser.add("--prior-file", default=None, help="The prior file")

    sampler_parser = parser.add_argument_group(title="Sampler arguments")
    sampler_parser.add(
        "--sampler",
        nargs="+",
        default="dynesty",
        help="Sampler to use, or a list of samplers to use",
    )
    sampler_parser.add(
        "--sampling-seed", default=None, type=int, help="Random sampling seed"
    )
    sampler_parser.add(
        "--n-parallel",
        type=int,
        default=1,
        help="Number of identical parallel jobs to run per event",
    )
    sampler_parser.add(
        "--sampler-kwargs",
        default=None,
        help=(
            "Channel dictionary: keys relate to the detector with values "
            "the channel name, e.g. 'GDS-CALIB_STRAIN'. Note, the "
            "dictionary should follow basic python dict syntax."
        ),
    )

    # Waveform arguments
    waveform_parser = parser.add_argument_group(title="Waveform arguments")
    waveform_parser.add(
        "--reference-frequency", default=20, type=float, help="The reference frequency"
    )
    waveform_parser.add(
        "--waveform-approximant",
        default="IMRPhenomPv2",
        type=str,
        help="The name of the waveform approximant",
    )
    waveform_parser.add(
        "--frequency-domain-source-model",
        default="lal_binary_black_hole",
        type=str,
        help=(
            "Name of the frequency domain source model. Can be one of"
            "[lal_binary_black_hole, lal_binary_neutron_star,"
            "lal_eccentric_binary_black_hole_no_spins, sinegaussian, "
            "supernova, supernova_pca_model]"
        ),
    )

    return parser
