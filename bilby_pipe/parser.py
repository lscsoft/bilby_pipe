from bilby_pipe.bilbyargparser import BilbyArgParser
from . import utils

__version__ = utils.get_version_information()


def create_parser(
    pipe_args=True,
    job_args=True,
    run_spec=True,
    pe_summary=True,
    injection=True,
    data_gen=True,
    waveform=True,
    generation=True,
    analysis=True,
):
    """ Creates the BilbyArgParser for bilby_pipe

    Parameters
    ----------
    run_spec: bool
        Add the `run_spec` argument group to the parser
    pe_summary: bool
        Add the `pe_summary` argument group to the parser
    injection: bool
        Add the `injection` argument group to the parser
    data_gen: bool
        Add the `data_gen` argument group to the parser
    waveform: bool
        Add the `waveform` argument group to the parser
    detector: bool
        Add the `detector` argument group to the parser

    Returns
    -------
    parser: BilbyArgParser instance
        Argument parser

    """
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

    if job_args:
        parser.add("--idx", type=int, help="The level A job index", default=0)
        parser.add("--cluster", type=str, help="The condor cluster ID", default=None)
        parser.add("--process", type=str, help="The condor process ID", default=None)

    if pipe_args:
        parser.add(
            "--accounting", type=str, required=True, help="Accounting group to use"
        )
        parser.add(
            "--local",
            action="store_true",
            help="Run the job locally, i.e., not through a batch submission",
        )
        parser.add(
            "--local-generation",
            action="store_true",
            help=(
                "Run the data generation job locally. Note that if you are "
                "running on a cluster where the compute nodes do not have "
                "internet access, e.g. on ARCCA, you will need to run the "
                "data generation job locally."
            ),
        )
        parser.add(
            "--submit",
            action="store_true",
            help="Attempt to submit the job after the build",
        )
        parser.add(
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
        parser.add(
            "--singularity-image",
            type=str,
            default=None,
            help="Singularity image to use",
        )

    if run_spec:
        parser.add("--label", type=str, default="label", help="Output label")
        parser.add("--outdir", type=str, default=".", help="Output directory")
        parser.add(
            "--sampler",
            nargs="+",
            default="dynesty",
            help="Sampler to use, or a list of samplers to use",
        )
        parser.add(
            "--detectors",
            action="append",
            help=(
                "The names of detectors to use. If given in the ini file, "
                "detectors are specified by `detectors=[H1, L1]`. If given "
                "at the command line, as `--detectors H1 --detectors L1`"
            ),
        )
        parser.add(
            "--coherence-test",
            action="store_true",
            help=(
                "Run the analysis for all detectors together and for each "
                "detector separately"
            ),
        )

    if pe_summary:
        pe_summary = parser.add_argument_group(title="Summary page arguments")
        pe_summary.add(
            "--create-summary", action="store_true", help="Create a summary page"
        )
        pe_summary.add(
            "--webdir",
            type=str,
            default=None,
            help=(
                "Directory to store summary pages. If not given, defaults to "
                "outdir/results_page"
            ),
        )
        pe_summary.add("--email", type=str, help="Email for notifications")
        pe_summary.add(
            "--existing-dir",
            type=str,
            default=None,
            help=(
                "If given, add results to an directory with an an existing"
                " summary.html file"
            ),
        )

    if injection:
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

    if data_gen:
        data_gen_pars = parser.add_argument_group(title="Data generation arguments")
        data_gen_pars.add("--gps-file", type=str, help="File containing GPS times")
        data_gen_pars.add("--gracedb", type=str, help="Gracedb UID", default=None)

    if waveform:
        parser.add(
            "--reference-frequency",
            default=20,
            type=float,
            help="The reference frequency",
        )
        parser.add(
            "--waveform-approximant",
            default="IMRPhenomPv2",
            type=str,
            help="The name of the waveform approximant",
        )
        parser.add(
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

    if generation:
        det_parser = parser.add_argument_group(title="Detector arguments")
        det_parser.add(
            "--calibration", type=int, default=2, help="Which calibration to use"
        )
        det_parser.add(
            "--duration",
            type=int,
            default=4,
            help="The duration of data around the event to use",
        )
        det_parser.add(
            "--trigger-time", default=None, type=float, help="The trigger time"
        )
        det_parser.add("--sampling-frequency", default=4096, type=int)
        det_parser.add(
            "--channel-names",
            default=None,
            nargs="*",
            help="Channel names to use, if not provided known "
            "channel names will be tested.",
        )
        det_parser.add(
            "--query-types",
            default=None,
            nargs="*",
            help="Query types to "
            "use. If not provided known query types will be tested.",
        )
        det_parser.add(
            "--psd-duration",
            default=500,
            type=int,
            help="Time used to generate the PSD, default is 500.",
        )
        det_parser.add("--minimum-frequency", default=20, type=float)

    if analysis:
        parser.add(
            "--data-label",
            default=None,
            help="Label used for the data dump",
            required=True,
        )
        parser.add(
            "--sampling-seed", default=None, type=int, help="Random sampling seed"
        )
        parser.add(
            "--default-prior",
            default="BBHPriorDict",
            type=str,
            help="The name of the prior set to base the prior on. Can be one of"
            "[PriorDict, BBHPriorDict, BNSPriorDict, CalibrationPriorDict]",
        )
        parser.add("--prior-file", default=None, help="The prior file")
        parser.add(
            "--deltaT",
            type=float,
            default=0.1,
            help=(
                "The symmetric width (in s) around the trigger time to"
                " search over the coalesence time"
            ),
        )
        parser.add(
            "--distance-marginalization",
            action="store_true",
            default=False,
            help="Boolean. If true, use a distance-marginalized likelihood",
        )
        parser.add(
            "--phase-marginalization",
            action="store_true",
            default=False,
            help="Boolean. If true, use a phase-marginalized likelihood",
        )
        parser.add(
            "--time-marginalization",
            action="store_true",
            default=False,
            help="Boolean. If true, use a time-marginalized likelihood",
        )
        parser.add("--sampler-kwargs", default=None)
        parser.add(
            "--create-plots",
            action="store_true",
            help="Create marginal 1D and corner plot after the analysis job",
        )

    return parser