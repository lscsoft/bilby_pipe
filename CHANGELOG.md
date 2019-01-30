# All notable changes will be documented in this file

## Unreleased

Changes currently on master, but not under a tag.

### Added
- Flag for running the data generation step on the local head node

### Changes
- Moved all command line argument logic to a single module with switches

## [0.0.3] 2018-01-14

### Added
- Support for pesummary module to produce summary files

### Changed
- Minor bug fixes for argument passing and result file naming

## [0.0.2] 2018-01-10

### Added
- Added singularity containers
- Add testing in python 3.5, 3.6, and 3.7
- Add a `--local` flag for testing/debug (runs the code on the host rather than submitting to a queue)
- Add a `--query_types` flag to specify list of LDRDataFind query types to use when building the `gw_data_find` command line

## [0.0.1] 2018-12-31

- First working version release with basic functionality
