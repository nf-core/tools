# ![nf-core/tools](docs/images/nf-core-logo.png)

## [nf-core/tools](https://github.com/nf-core/tools)
[![Build Status](https://travis-ci.org/nf-core/tools.svg?branch=master)](https://travis-ci.org/nf-core/tools)
[![codecov](https://codecov.io/gh/nf-core/tools/branch/master/graph/badge.svg)](https://codecov.io/gh/nf-core/tools)
[![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg?style=flat-square)](http://bioconda.github.io/recipes/nf-core/README.html)

A python package with helper tools for the nf-core community.

## Table of contents

* [Installation](#installation)
* [Listing pipelines](#listing-pipelines) (`nf-core list`)
* [Downloading pipelines for offline use](#downloading-pipelines-for-offline-use) (`nf-core download`)
* [Listing software licences](#pipeline-software-licences): List software licences for a given workflow (`nf-core licences`)
* [Creating a new workflow](#creating-a-new-workflow) (`nf-core create`)
* [Checking a pipeline against nf-core guidelines](#linting-a-workflow) (`nf-core lint`)
* [Bumping a pipeline version number](#bumping-a-pipeline-version-number) (`nf-core bump-version`)

## Installation

You can install `nf-core/tools` from [PyPI](https://pypi.python.org/pypi/nf-core/) using pip as follows:

```bash
pip install nf-core
```

If you would like the development version instead, the command is:

```bash
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

```bash
$ nf-core list

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'


Name               Version    Published    Last Pulled    Default local is latest release?
-----------------  ---------  -----------  -------------  ----------------------------------
nf-core/hlatyping  1.1.0      5 days ago   9 minutes ago  Yes
nf-core/methylseq  1.1        1 week ago   2 months ago   No
nf-core/chipseq    dev        -            -              No
nf-core/eager      dev        -            -              No
nf-core/exoseq     dev        -            -              No
nf-core/mag        dev        -            -              No
nf-core/rnaseq     dev        -            -              No
nf-core/smrnaseq   dev        -            -              No
nf-core/vipr       dev        -            -              No
```

To narrow down the list, supply one or more additional keywords to filter the pipelines based on matches in titles, descriptions and topics:

```bash
nf-core list rna rna-seq

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'


Name              Version    Published     Last Pulled    Default local is latest release?
----------------  ---------  ------------  -------------  ----------------------------------
nf-core/rnaseq    1.0        20 hours ago  -              No
nf-core/smrnaseq  dev        -             -              No
```

You can sort the results by latest release (default), name (alphabetical) or number of GitHub stars using the `-s`/`--stars` option.

Finally, to return machine-readable JSON output, use the `--json` flag.


## Downloading pipelines for offline use
Sometimes you may need to run an nf-core pipeline on a server or HPC system that has no internet connection. In this case you will need to fetch the pipeline files first, then manually transfer them to your system.

To make this process easier and ensure accurate retrieval of correctly versioned code and software containers, we have written a download helper tool. Simply specify the name of the nf-core pipeline and it will be downloaded to your current working directory.

By default, the pipeline will just download the pipeline code. If you specify the flag `--singularity`, it will also download any singularity image files that are required.

```bash
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

```bash
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

```bash
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

## Creating a new workflow
The `create` subcommand makes a new workflow using the nf-core base template.
With a given pipeline name, description and author, it makes a starter pipeline which follows nf-core best practices.

After creating the files, the command initialises the folder as a git repository and makes an initial commit. This first "vanilla" commit which is identical to the output from the templating tool is important, as it allows us to keep your pipeline in sync with the base template in the future.
See the [nf-core syncing docs](http://nf-co.re/sync) for more information.

```bash
$ nf-core create

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

Workflow Name: nextbigthing
Description: This pipeline analyses data from the next big 'omics technique
Author: Big Steve

INFO: Creating new nf-core pipeline: nf-core/nextbigthing

INFO: Initialising pipeline git repository

INFO: Done. Remember to add a remote and push to GitHub:
  cd /path/to/nf-core-nextbigthing
  git remote add origin git@github.com:USERNAME/REPO_NAME.git
  git push
```

Once you have run the command, create a new empty repository on GitHub under your username (not the `nf-core` organisation, yet).
On your computer, add this repository as a git remote and push to it:

```bash
git remote add origin https://github.com/ewels/nf-core-nextbigthing.git
git push --set-upstream origin master
```

You can then continue to edit, commit and push normally as you build your pipeline.

Please see the [nf-core documentation](https://nf-co.re/adding_pipelines) for a full walkthrough of how to create a new nf-core workflow.

Note that if the required arguments for `nf-core create` are not given, it will interactively prompt for them. If you prefer, you can supply them as command line arguments. See `nf-core create --help` for more information.


## Linting a workflow
The `lint` subcommand checks a given pipeline for all nf-core community guidelines.
This is the same test that is used on the automated continuous integration tests.

For example, the current version looks something like this:

```bash
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

You can find extensive documentation about each of the lint tests in the [lint errors documentation](https://nf-co.re/errors).


## Bumping a pipeline version number

When releasing a new version of a nf-core pipeline, version numbers have to be updated in several different places. The helper command `nf-core bump-version` automates this for you to avoid manual errors (and frustration!).

The command uses results from the linting process, so will only work with workflows that pass these tests.

Usage is `nf-core bump-version <pipeline_dir> <new_version>`, eg:

```bash
$ cd path/to/my_pipeline
$ nf-core bump-version . 1.0

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
  96 tests passed   0 tests had warnings   0 tests failed

INFO: Changing version number:
  Current version number is '1.0dev'
  New version number will be '1.0'

INFO: Updating version in nextflow.config
 - version = '1.0dev'
 + version = '1.0'

INFO: Updating version in nextflow.config
 - container = 'nfcore/mypipeline:dev'
 + container = 'nfcore/mypipeline:1.0'

INFO: Updating version in .travis.yml
 - docker tag nfcore/mypipeline:dev nfcore/mypipeline:latest
 + docker tag nfcore/mypipeline:dev nfcore/mypipeline:1.0

INFO: Updating version in Singularity
 - VERSION 1.0dev
 + VERSION 1.0

INFO: Updating version in environment.yml
 - name: nf-core-mypipeline-1.0dev
 + name: nf-core-mypipeline-1.0

INFO: Updating version in Dockerfile
 - PATH /opt/conda/envs/nf-core-mypipeline-1.0dev/bin:$PATH
 + PATH /opt/conda/envs/nf-core-mypipeline-1.0/bin:\$PATH

INFO: Updating version in Singularity
 - PATH=/opt/conda/envs/nf-core-mypipeline-1.0dev/bin:$PATH
 + PATH=/opt/conda/envs/nf-core-mypipeline-1.0/bin:\$PATH
```

To change the required version of Nextflow instead of the pipeline version number, use the flag `--nextflow`.
