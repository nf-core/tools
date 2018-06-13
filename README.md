<img src="docs/images/nf-core-logo.png" width="400">

# [nf-core/tools](https://github.com/nf-core/tools)
[![Build Status](https://travis-ci.org/nf-core/tools.svg?branch=master)](https://travis-ci.org/nf-core/tools)
[![codecov](https://codecov.io/gh/nf-core/tools/branch/master/graph/badge.svg)](https://codecov.io/gh/nf-core/tools)

A python package with helper tools for the nf-core community.

## Table of contents

* [Installation instructions](#installation)
* [`nf-core list`](#listing-pipelines): List nf-core pipelines with local info
* [`nf-core download`](#downloading-pipelines-for-offline-use): Download a pipeline and singularity container
* [`nf-core licences`](#pipeline-software-licences): List software licences for a given workflow
* [`nf-core lint`](#linting-a-workflow): Check pipeline against nf-core guidelines
* [`nf-core release`](#making-a-pipeline-release): Update nf-core pipeline version number

## Installation

You can install `nf-core/tools` from [PyPI](https://pypi.python.org/pypi/nf-core/) using pip as follows:

```
pip install nf-core
```

If you would like the development version instead, the command is:

```
pip install --upgrade --force-reinstall git+https://github.com/nf-core/tools.git
```

Alternatively, if you would like to edit the files locally:

```bash
# Clone the repository code - you should probably specify your fork instead
git clone https://github.com/nf-core/tools.git nf-core-tools
cd nf-core-tools

# Install the package
python setup.py develop

# Alternatively, install with pip
pip install -e .
```

## Listing pipelines
The command `nf-core list` shows all available nf-core pipelines along with their latest version,  when that was published and how recently the pipeline code was pulled to your local system (if at all).

An example of the output from the command is as follows:

```
$ nf-core list

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'


Name               Version    Published       Last Pulled    Default local is latest release?
-----------------  ---------  --------------  -------------  ----------------------------------
nf-core/methylseq  1.0        1.0 months ago  just now       Yes
nf-core/chipseq    dev        -               -              No
nf-core/EAGER2.0   dev        -               -              No
nf-core/exoseq     dev        -               -              No
nf-core/mag        dev        -               -              No
nf-core/rnaseq     dev        -               -              No
nf-core/vipr       dev        -               -              No
```

## Downloading pipelines for offline use
Sometimes you may need to run an nf-core pipeline on a server or HPC system that has no internet connection. In this case you will need to fetch the pipeline files first, then manually transfer them to your system.

To make this process easier and ensure accurate retrieval of correctly versioned code and software containers, we have written a download helper tool. Simply specify the name of the nf-core pipeline and it will be downloaded to your current working directory.

By default, the pipeline will just download the pipeline code. If you specify the flag `--singularity`, it will also download any singularity image files that are required.

```
$ nf-core download methylseq --singularity

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'


INFO: Saving methylseq
 Pipeline release: 1.0
 Pull singularity containers: Yes
 Output directory: nf-core-methylseq-1.0

INFO: Downloading workflow files from GitHub

INFO: Downloading 1 singularity container
nf-core-methylseq-1.0.simg [762.28MB]  [####################################]  780573/780572
```
```
$ tree -L 2 nf-core-methylseq-1.0/

nf-core-methylseq-1.0/
├── singularity-images
│   └── nf-core-methylseq-1.0.simg
└── workflow
    ├── CHANGELOG.md
    ├── Dockerfile
    ├── LICENCE.md
    ├── README.md
    ├── assets
    ├── bin
    ├── conf
    ├── docs
    ├── environment.yml
    ├── main.nf
    ├── nextflow.config
    └── tests

7 directories, 8 files
```

## Pipeline software licences
Sometimes it's useful to see the software licences of the tools used in a pipeline. You can use the `licences` subcommand to fetch and print the software licence from each conda / PyPI package used in an nf-core pipeline.

```
$ nf-core licences rnaseq

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'


INFO: Warning: This tool only prints licence information for the software tools packaged using conda.
        The pipeline may use other software and dependencies not described here.

Package Name           Version    Licence
---------------------  ---------  --------------------
stringtie              1.3.3      Artistic License 2.0
preseq                 2.0.3      GPL
trim-galore            0.4.5      GPL
bioconductor-edger     3.20.7     GPL >=2
fastqc                 0.11.7     GPL >=3
openjdk                8.0.144    GPLv2
r-gplots               3.0.1      GPLv2
r-markdown             0.8        GPLv2
rseqc                  2.6.4      GPLv2
bioconductor-dupradar  1.8.0      GPLv3
hisat2                 2.1.0      GPLv3
multiqc                1.5        GPLv3
r-data.table           1.10.4     GPLv3
star                   2.5.4a     GPLv3
subread                1.6.1      GPLv3
picard                 2.18.2     MIT
samtools               1.8        MIT
```


## Linting a workflow
The `lint` subcommand checks a given pipeline for all nf-core community guidelines.
This is the same test that is used on the automated continuous integration tests.

For example, the current version looks something like this:

```
$ cd path/to/my_pipeline
$ nf-core lint .

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

Running pipeline tests  [####################################]  100%  None

INFO: ===========
 LINTING RESULTS
=================
  72 tests passed   2 tests had warnings   0 tests failed

WARNING: Test Warnings:
  http://nf-co.re/errors#8: Conda package is not latest available: picard=2.18.2, 2.18.6 available
  http://nf-co.re/errors#8: Conda package is not latest available: bwameth=0.2.0, 0.2.1 available
```

You can find extensive documentation about each of the lint tests in the [lint errors documentation](docs/lint_errors.md).


## Making a pipeline release

When releasing a new version of a nf-core pipeline, version numbers have to be updated in several different places. The helper command `nf-core release` automates this for you to avoid manual errors (and frustration!).

The command uses results from the linting process, so will only work with workflows that pass these tests.

Usage is `nf-core release <pipeline_dir> <new_version>`, eg:

```
$ cd path/to/my_pipeline
$ nf-core release . 1.3


                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'


INFO: Running nf-core lint tests
Running pipeline tests  [####################################]  100%  None

INFO: ===========
 LINTING RESULTS
=================
  74 tests passed   0 tests had warnings   0 tests failed

INFO: Changing version number:
  Current version number is '1.3dev'
  New version number will be '1.3'

INFO: Updating version in nextflow.config
 - version = '1.3dev'
 + version = '1.3'

INFO: Updating version in nextflow.config
 - container = 'nfcore/methylseq:latest'
 + container = 'nfcore/methylseq:1.3'

INFO: Updating version in Singularity
 - VERSION 1.3dev
 + VERSION 1.3

INFO: Updating version in environment.yml
 - name: nfcore-methylseq-1.3dev
 + name: nfcore-methylseq-1.3

INFO: Updating version in Dockerfile
 - ENV PATH /opt/conda/envs/nfcore-methylseq-1.3dev/bin:$PATH
 + ENV PATH /opt/conda/envs/nfcore-methylseq-1.3/bin:$PATH

INFO: Updating version in Singularity
 - PATH=/opt/conda/envs/nfcore-methylseq-1.3dev/bin:$PATH
 + PATH=/opt/conda/envs/nfcore-methylseq-1.3/bin:$PATH
```
