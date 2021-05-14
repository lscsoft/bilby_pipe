# All notable changes will be documented in this file

## v1.0.4: 2021-05-14
### Changes
- Allow different result file formats (!395)
- Address minor bugs (!394, !399)
- Add dtype kwarg to TimeSeries.get call (!401)
- Fixes to dependencies (!398, !404)

### Added
- Add parallelisation of bilby_mcmc (!397)
- Added zero likelihood option (!396)

## v1.0.3: 2021-02-17
### Changes
- Clean up the submit scripts, fixing bugs in the OSG (!380, !389, !387, !386)
- Force the use of outdirs to prevent complications (!382)
- Regenerate look-up tables based on new distance priors (!381)

### Added
- Allow data from tape (!385)
- Enable extra detectors (!383)
- Behaviour to prevent overwriting of directories (!375)
- Checking of duplicate entries (!372)
- Option to pass through the conversion functions (!373)

## v1.0.1: 2020-26-08
### Changed
- Updated bilby dependency to v1.0.2
- Enable support for the OSG and documentation (!364)
- PESummary now pointed to the "complete" config files (!366)
- Fixed bug related to nested outdir (!365)
- Add support for numerical relativity injection file (!361)
- Add support for generic waveform-arguments (!361)
- Improve behaviour for specifying single mode (!362)
- Improve slurm documentation and version information (!363, !362)
- Improve suppory for multi-line prior-dicts (!369)

## v1.0.1: 2020-26-08
### Added
- Priority setting for condor
- Email notofications

### Changed
- Python 3.6+ requirement
- Review files to use reference frequency of 100Hz
- Improved parent-child relation to avoid recreating cached files
- Job creation modularised
- Overhaul and improvements to the slurm backend


## v1.0.00: 2020-27-07
### Added
- Trigger-time now able to use event names (!333)
- Add option to pass in ROQ weight file directly (!340)
- Prior check and print-out and run time and sampler check (!337, !338)

### Changes
- Modularation of the main module (!336)
- Documentation bug fixes and versioning (!341 !343)

## v0.3.12: 2020-15-04
### Added
- Add support for the sky-frame in bilby 0.6.8
- Add support for post processing individual results

### Changes
- Fixed a bug in the periodic restart time

## v0.3.11: 2020-15-04

### Changes
-   Put periodic restart into job submission parser (!306)
-   Injection number fix (!281)
-   Changes to data read-in logic (!305)
-   Update lookup tables following changes in bilby (!307)
-   Remove hardcoded checkpoint from review runs (!309)
-   Fix issues with checkpointing (!308)
-   Remove future imports (!310)
-   Fix bug where request-cpu value was not passed through (!311)
-   Allow lal resampling (!312)

## v0.3.10 : 2020-30-03

### Added
-   Waveform arguments (!296)
-   prior-dict option (!288)
-   Variable waveform generator class (!283)
-   Calibration in injections (!282)
-   Likelihood kwargs (!285)

### Changes
-   Improved --help message (!298)
-   Update to date calibration files for online runs
-   Improvements to the review tests script (!286)
-   Documentation on injections (!275)

## v0.3.9 : 2020-30-03

### Changes
-   Update documentation for using CVMFS
-   Allow other samplers in the review script
-   Fix the timeslide check
-   Tweak the generation: add read methods for gwp, txt and hdf5 and improve PSD data handling
-   Use the generated complete config file at run time
-   Add an XML conversion method

## v0.3.8 : 2020-01-03
-   Minor release updating to bilby v0.6.3

## v0.3.7 : 2019-12-20
-   Minor release updating to bilby v0.6.2

### Changes
-   Fixes ROQ scaling issues
-   Modifies Default and FastTest sampler settings
-   Edits template priors to allow component mass scaling

## v0.3.6 : 2019-12-10
-   Minor release fixing bugs with the ROQ

## v0.3.5 : 2019-12-06
-   Minor release following small fixes

### Added
-   PESummary CI test
-   Mass 1 constraint to prior files

### Changes
-   Fix --convert-to-flat-in-component-mass flag
-   Pass the ROQ scale factor to the likelihood
-   Fix ROQ waveform plotting
-   Set max skymaps points to 5000

## v0.3.4 : 2019-12-02
-   Minor version release updating to bilby v0.6.1
-   Remove reflective boundaries from defaults priors
-   Resolve issue with ROQ times steps and the PSD roll off (!230)
-   Update the minimum pesummary version

## v0.3.3 : 2019-11-26
-   Minor release following small fixes

### Changes
-   All gracedb jobs default to "vanilla" universe
-   Fixes dict conversion error of reading negative numbers
-   Minor fix to gwdata paths

## v0.3.2 : 2019-11-13

### Added
-   GWpy data quality check
-   GWpy spectrogram plotting method
-   Method to apply timeshifts with example
-   Option to generate injection with different waveform to PE

### Changes
-   Fix to prior limits for actual spin maximum
-   Updated calls to pesummary
-   Minor improvements to gracedb script

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
