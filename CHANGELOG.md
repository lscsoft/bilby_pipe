# All notable changes will be documented in this file

## v0.2.1 : 2019-06-05
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
