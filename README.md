# bilby_pipe

A package for automating transient gravitational wave parameter estimation

## Installation

Clone the repository then run

```bash
$ python setup.py install
```

This will install all dependencies. Currently, it assumes you have access to a
working version of `gw_data_find` without explicitly pointing it to the server
(i.e., that you are working on one of the LDG clusters).

## Example

In this example, we call :code:`bilby_pipe` for the gracedb event G184098,
which is GW150914. Other required inputs are the executable to run, and the
accounting group.

```bash
$ bilby_pipe --gracedb G184098 --label GW150914 --executable script.py --accounting ligo.dev.o3.cbc.pe.lalinference
23:16 bilby_pipe INFO    : Starting routine to download GraceDb candidate G184098
23:16 bilby_pipe INFO    : Initialise client and attempt to download
23:16 bilby_pipe INFO    : Successfully downloaded candidate
23:16 bilby_pipe INFO    : Writing candidate to PE_G184098_GW150914/G184098.json
23:16 bilby_pipe INFO    : Building gw_data_find command line
23:16 bilby_pipe INFO    : Using LDRDataFind query type H1_HOFT_C02
23:16 bilby_pipe INFO    : Now executing: gw_data_find --observatory H --gps-start-time 1126259458.391 --gps-end-time 1126259462.391 --type H1_HOFT_C02 --output PE_G184098_GW150914/H1-H1_HOFT_C02_CACHE-1126259458.391-4.lcf --url-type file --lal-cache
23:16 bilby_pipe INFO    : Building gw_data_find command line
23:16 bilby_pipe INFO    : Using LDRDataFind query type L1_HOFT_C02
23:16 bilby_pipe INFO    : Now executing: gw_data_find --observatory L --gps-start-time 1126259458.391 --gps-end-time 1126259462.391 --type L1_HOFT_C02 --output PE_G184098_GW150914/L1-L1_HOFT_C02_CACHE-1126259458.391-4.lcf --url-type file --lal-cache
The directory PE_G184098_GW150914/logs doesn't exist, creating it...
```

This generates a directory :code:`PE_G184098_GW150914` which has the following structure

```bash
$ ls PE_G184098_GW150914
logs
G184098.json
H1-H1_HOFT_C02_CACHE-1126259458.391-4.lcf
L1-L1_HOFT_C02_CACHE-1126259458.391-4.lcf
script.py_20180926_01.submit
```

The file :code:`G184098.json` contains all the event data available from Gracedb.
There are then also two cache files and a submit script

```bash
$ cat PE_G184098_GW150914/script.py_20180926_01.submit
universe = vanilla
executable = script.py
getenv = True
notification = never
log = PE_G184098_GW150914/logs/script.py_20180926_01.log
output = PE_G184098_GW150914/logs/script.py_20180926_01.output
error = PE_G184098_GW150914/logs/script.py_20180926_01.error
accounting_group=ligo.dev.o3.cbc.pe.lalinference
arguments = --frames PE_G184098_GW150914/H1-H1_HOFT_C02_CACHE-1126259458.391-4.lcf PE_G184098_GW150914/L1-L1_HOFT_C02_CACHE-1126259458.391-4.lcf
```
