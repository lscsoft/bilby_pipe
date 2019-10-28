# All notable changes will be documented in this file

## v0.3.1 : 2019-10-29

### Added
-   Flag for use of online PE dedicated nodes

### Changes
-   Fixed trigger time to zero for simulations
-   Writes review.ini to top level

## v0.3.0 : 2019-10-25
Major release with overhaul of main interface

### Added
-   Support for using n-parallel with other tools
-   Support for running on gps_time with injections
-   Default to file_transfer=True
-   Testing running ini files in biby-test-mode
-   Default and fast-PE sampler-kwarg settings

### Changes
-   Expanded default prior limits
-   PSD defaults updated to max at 1024 (user override available)
-   Data dump process changes

## v0.2.7 : 2019-10-02
Minor release following small fixes

## v0.2.6 : 2019-09-23
### Added
-   Testing of min/max frequencies
-   A warning message for cases when "tidal" waveforms are used without the appropriate frequency domain source model

### Changes
-   Improvements to the gracedb parsing in preparation for online running
-   Improvements to the logging output

## v0.2.5 : 2019-08-22
### Changes
-   Fixed bug in time-jitter option (default was None, now True)

## v0.2.4 : 2019-08-22
### Added
-   Support for use on a slurm filesystem
-   Limited support for a user-defined likelihood

### Changes
-   Improvements to the gracedb script (changes to the filenames and channels)

## v0.2.3 : 2019-08-15

### Changed
-   Removed testing against python3.5: it was found that the
    python-ldas-tools-framecpp package was no longer compatible with python3.5.
    As such, this breaks the C.I. testing environment. While basic running is
    still expected to work with python3.5, it is strongly recommended people
    update to a modern python installation.
-   Update to the review defaults and online running settings
-   Fixed bug when sampler_kwargs is None
-   Allow users to specific external source functions
-   Fix standard priors to have hign-spin (0.8) upper boundaries
-   Add time jittering option
-   Add shell script

## v0.2.2 : 2019-06-19
Release coinciding with bilby 0.5.2. Minor changes fixing bugs in 0.5.2 only

### Changed
-   Fix issues in ROQ rescaling
-   Remove print os environ statement
-   Add summary pages to fiducial runs
-   Fix minor bugs in the pp tests
-   Increase default periodic restart time to 12hrs 
-   Tweak plotting script
-   Remove double escape from priors
-   Review ini files not written to outdir
-   Compatibility issues with bilby 0.5.2


## v0.2.1 : 2019-06-18
Release coinciding with bilby 0.5.2

### Added
-   Automated rescaling
-   Automated calibration
-   pesummary as a dependency

## v0.2.0 : 2019-06-05
Release coinciding with bilby 0.5.1, planned for initial review

### Added
-   Gaussian noise flag
-   Review script
-   Gracedb module and CLI
-   Plotting module and CLI
-   PP-test module and CLI

### Changed
-   examples_ini_file -> examples 
-   Many bug fixes

## v0.1.0 : 2019-04-29

### Added
-   Calibration, ROQ, PSD estimation, data-setting methods, etc

## v0.0.4 : 2019-03-05

### Added
-   Flag for running the data generation step on the local head node
-   Flag for setting random seeds

### Changes
-   Moved all command line argument logic to a single module with switches
-   Moved data generation to use gwpy only
-   Moved PSD generation t use gwpy only

## v0.0.3 : 2019-01-14

### Added
-   Support for pesummary module to produce summary files

### Changed
-   Minor bug fixes for argument passing and result file naming

## v0.0.2 : 2019-01-10

### Added
-   Added singularity containers
-   Add testing in python 3.5, 3.6, and 3.7
-   Add a `--local` flag for testing/debug (runs the code on the host rather than submitting to a queue)
-   Add a `--query_types` flag to specify list of LDRDataFind query types to use when building the `gw_data_find` command line

## [0.0.1] 2018-12-31

-   First working version release with basic functionality
