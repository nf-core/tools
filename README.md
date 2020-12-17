# ![nf-core/tools](docs/images/nfcore-tools_logo.png) <!-- omit in toc -->

[![Python tests](https://github.com/nf-core/tools/workflows/Python%20tests/badge.svg?branch=master&event=push)](https://github.com/nf-core/tools/actions?query=workflow%3A%22Python+tests%22+branch%3Amaster)
[![codecov](https://codecov.io/gh/nf-core/tools/branch/master/graph/badge.svg)](https://codecov.io/gh/nf-core/tools)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[![install with Bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](https://bioconda.github.io/recipes/nf-core/README.html)
[![install with PyPI](https://img.shields.io/badge/install%20with-PyPI-blue.svg)](https://pypi.org/project/nf-core/)
[![Get help on Slack](http://img.shields.io/badge/slack-nf--core%20%23tools-4A154B?logo=slack)](https://nfcore.slack.com/channels/tools)

A python package with helper tools for the nf-core community.

> **Read this documentation on the nf-core website: [https://nf-co.re/tools](https://nf-co.re/tools)**

## Table of contents <!-- omit in toc -->

* [`nf-core` tools installation](#installation)
* [`nf-core list` - List available pipelines](#listing-pipelines)
* [`nf-core launch` - Run a pipeline with interactive parameter prompts](#launch-a-pipeline)
* [`nf-core download` - Download pipeline for offline use](#downloading-pipelines-for-offline-use)
* [`nf-core licences` - List software licences in a pipeline](#pipeline-software-licences)
* [`nf-core create` - Create a new workflow from the nf-core template](#creating-a-new-workflow)
* [`nf-core lint` - Check pipeline code against nf-core guidelines](#linting-a-workflow)
* [`nf-core schema` - Work with pipeline schema files](#working-with-pipeline-schema)
* [`nf-core bump-version` - Update nf-core pipeline version number](#bumping-a-pipeline-version-number)
* [`nf-core sync` - Synchronise pipeline TEMPLATE branches](#sync-a-pipeline-with-the-template)
* [Citation](#citation)

The nf-core tools package is written in Python and can be imported and used within other packages.
For documentation of the internal Python functions, please refer to the [Tools Python API docs](https://nf-co.re/tools-docs/).

## Installation

### Bioconda

You can install `nf-core/tools` from [bioconda](https://bioconda.github.io/recipes/nf-core/README.html).

First, install conda and configure the channels to use bioconda
(see the [bioconda documentation](https://bioconda.github.io/user/install.html)).
Then, just run the conda installation command:

```bash
conda install nf-core
```

Alternatively, you can create a new environment with both nf-core/tools and nextflow:

```bash
conda create --name nf-core python=3.7 nf-core nextflow
conda activate nf-core
```

### Python Package Index

`nf-core/tools` can also be installed from [PyPI](https://pypi.python.org/pypi/nf-core/) using pip as follows:

```bash
pip install nf-core
```

### Development version

If you would like the latest development version of tools, the command is:

```bash
pip install --upgrade --force-reinstall git+https://github.com/nf-core/tools.git@dev
```

If you intend to make edits to the code, first make a fork of the repository and then clone it locally.
Go to the cloned directory and install with pip (also installs development requirements):

```bash
pip install --upgrade -r requirements-dev.txt -e .
```

### Using a specific Python interpreter

If you prefer, you can also run tools with a specific Python interpreter.
The command line usage and flags are then exactly the same as if you ran with the `nf-core` command.
Note that the module is `nf_core` with an underscore, not a hyphen like the console command.

For example:

```bash
python -m nf_core --help
python3 -m nf_core list
~/my_env/bin/python -m nf_core create --name mypipeline --description "This is a new skeleton pipeline"
```

### Using with your own Python scripts

The tools functionality is written in such a way that you can import it into your own scripts.
For example, if you would like to get a list of all available nf-core pipelines:

```python
import nf_core.list
wfs = nf_core.list.Workflows()
wfs.get_remote_workflows()
for wf in wfs.remote_workflows:
    print(wf.full_name)
```

Please see [https://nf-co.re/tools-docs/](https://nf-co.re/tools-docs/) for the function documentation.

### Automatic version check

nf-core/tools automatically checks the web to see if there is a new version of nf-core/tools available.
If you would prefer to skip this check, set the environment variable `NFCORE_NO_VERSION_CHECK`. For example:

```bash
export NFCORE_NO_VERSION_CHECK=1
```

## Listing pipelines

The command `nf-core list` shows all available nf-core pipelines along with their latest version,  when that was published and how recently the pipeline code was pulled to your local system (if at all).

An example of the output from the command is as follows:

```console
$ nf-core list

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10

┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Pipeline Name     ┃ Stars ┃ Latest Release ┃      Released ┃  Last Pulled ┃ Have latest release?  ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ rnafusion         │    45 │          1.2.0 │   2 weeks ago │            - │ -                     │
│ hic               │    17 │          1.2.1 │   3 weeks ago │ 4 months ago │ No (v1.1.0)           │
│ chipseq           │    56 │          1.2.0 │   4 weeks ago │  4 weeks ago │ No (dev - bfe7eb3)    │
│ atacseq           │    40 │          1.2.0 │   4 weeks ago │  6 hours ago │ No (master - 79bc7c2) │
│ viralrecon        │    20 │          1.1.0 │  1 months ago │ 1 months ago │ Yes (v1.1.0)          │
│ sarek             │    59 │          2.6.1 │  1 months ago │            - │ -                     │
[..truncated..]
```

To narrow down the list, supply one or more additional keywords to filter the pipelines based on matches in titles, descriptions and topics:

```console
$ nf-core list rna rna-seq

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10

┏━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Pipeline Name ┃ Stars ┃ Latest Release ┃      Released ┃ Last Pulled ┃ Have latest release? ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ rnafusion     │    45 │          1.2.0 │   2 weeks ago │           - │ -                    │
│ rnaseq        │   207 │          1.4.2 │  9 months ago │  5 days ago │ Yes (v1.4.2)         │
│ smrnaseq      │    12 │          1.0.0 │ 10 months ago │           - │ -                    │
│ lncpipe       │    18 │            dev │             - │           - │ -                    │
└───────────────┴───────┴────────────────┴───────────────┴─────────────┴──────────────────────┘
```

You can sort the results by latest release (`-s release`, default),
when you last pulled a local copy (`-s pulled`),
alphabetically (`-s name`),
or number of GitHub stars (`-s stars`).

```console
$ nf-core list -s stars

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10

┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Pipeline Name     ┃ Stars ┃ Latest Release ┃      Released ┃  Last Pulled ┃ Have latest release?  ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ rnaseq            │   207 │          1.4.2 │  9 months ago │   5 days ago │ Yes (v1.4.2)          │
│ sarek             │    59 │          2.6.1 │  1 months ago │            - │ -                     │
│ chipseq           │    56 │          1.2.0 │   4 weeks ago │  4 weeks ago │ No (dev - bfe7eb3)    │
│ methylseq         │    47 │            1.5 │  4 months ago │            - │ -                     │
│ rnafusion         │    45 │          1.2.0 │   2 weeks ago │            - │ -                     │
│ ampliseq          │    41 │          1.1.2 │  7 months ago │            - │ -                     │
│ atacseq           │    40 │          1.2.0 │   4 weeks ago │  6 hours ago │ No (master - 79bc7c2) │
[..truncated..]
```

To return results as JSON output for downstream use, use the `--json` flag.

Archived pipelines are not returned by default. To include them, use the `--show_archived` flag.

## Launch a pipeline

Some nextflow pipelines have a considerable number of command line flags that can be used.
To help with this, the `nf-core launch` command uses an interactive command-line wizard tool to prompt you for
values for running nextflow and the pipeline parameters.

The tool uses the `nextflow_schema.json` file from a pipeline to give parameter descriptions, defaults and grouping.
If no file for the pipeline is found, one will be automatically generated at runtime.

Nextflow `params` variables are saved in to a JSON file called `nf-params.json` and used by nextflow with the `-params-file` flag.
This makes it easier to reuse these in the future.

The `nf-core launch` command is an interactive command line tool and prompts you to overwrite the default values for each parameter.
Entering `?` for any parameter will give a full description from the documentation of what that value does.

```console
$ nf-core launch rnaseq

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10


INFO: [✓] Pipeline schema looks valid

INFO: This tool ignores any pipeline parameter defaults overwritten by Nextflow config files or profiles

? Nextflow command-line flags  (Use arrow keys)
 ❯ Continue >>
   ---------------
   -name
   -revision
   -profile
   -work-dir
   -resume
```

Once complete, the wizard will ask you if you want to launch the Nextflow run.
If not, you can copy and paste the Nextflow command with the `nf-params.json` file of your inputs.

```console
? Nextflow command-line flags  Continue >>
? Input/output options  input

Input FastQ files. (? for help)
? input  data/*{1,2}.fq.gz
? Input/output options  Continue >>
? Reference genome options  Continue >>

INFO: [✓] Input parameters look valid

INFO: Nextflow command:
  nextflow run nf-core-testpipeline/ -params-file "nf-params.json"


Do you want to run this command now? [y/N]: n
```

### Launch tool options

* `-c`, `--command-only`
  * If you prefer not to save your inputs in a JSON file and use `-params-file`, this option will specify all entered params directly in the nextflow command.
* `-p`, `--params-in PATH`
  * To use values entered in a previous pipeline run, you can supply the `nf-params.json` file previously generated.
  * This will overwrite the pipeline schema defaults before the wizard is launched.
* `-o`, `--params-out PATH`
  * Path to save parameters JSON file to. (Default: `nf-params.json`)
* `-a`, `--save-all`
  * Without this option the pipeline will ignore any values that match the pipeline schema defaults.
  * This option saves _all_ parameters found to the JSON file.
* `-h`, `--show-hidden`
  * A pipeline JSON schema can define some parameters as 'hidden' if they are rarely used or for internal pipeline use only.
  * This option forces the wizard to show all parameters, including those labelled as 'hidden'.

## Downloading pipelines for offline use

Sometimes you may need to run an nf-core pipeline on a server or HPC system that has no internet connection. In this case you will need to fetch the pipeline files first, then manually transfer them to your system.

To make this process easier and ensure accurate retrieval of correctly versioned code and software containers, we have written a download helper tool. Simply specify the name of the nf-core pipeline and it will be downloaded to your current working directory.

By default, the pipeline will download the pipeline code and the [institutional nf-core/configs](https://github.com/nf-core/configs) files.
If you specify the flag `--singularity`, it will also download any singularity image files that are required.

Use `-r`/`--release` to download a specific release of the pipeline. If not specified, the tool will automatically fetch the latest release.

```console
$ nf-core download methylseq -r 1.4 --singularity

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10

  INFO     Saving methylseq
            Pipeline release: 1.4
            Pull singularity containers: No
            Output file: nf-core-methylseq-1.4.tar.gz
  INFO     Downloading workflow files from GitHub
  INFO     Downloading centralised configs from GitHub
  INFO     Compressing download..
  INFO     Command to extract files: tar -xzf nf-core-methylseq-1.4.tar.gz
  INFO     MD5 checksum for nf-core-methylseq-1.4.tar.gz: 4d173b1cb97903dbb73f2fd24a2d2ac1
```

The tool automatically compresses all of the resulting file in to a `.tar.gz` archive.
You can choose other formats (`.tar.bz2`, `zip`) or to not compress (`none`) with the `-c`/`--compress` flag.
The console output provides the command you need to extract the files.

Once uncompressed, you will see the following file structure for the downloaded pipeline:

```console
$ tree -L 2 nf-core-methylseq-1.4/

nf-core-methylseq-1.4
├── configs
│   ├── bin
│   ├── conf
│   ├── configtest.nf
│   ├── docs
│   ├── LICENSE
│   ├── nextflow.config
│   ├── nfcore_custom.config
│   └── README.md
├── singularity-images
│   └── nf-core-methylseq-1.4.simg
└── workflow
    ├── assets
    ├── bin
    ├── CHANGELOG.md
    ├── CODE_OF_CONDUCT.md
    ├── conf
    ├── Dockerfile
    ├── docs
    ├── environment.yml
    ├── LICENSE
    ├── main.nf
    ├── nextflow.config
    ├── nextflow_schema.json
    └── README.md

10 directories, 15 files
```

The pipeline files are automatically updated so that the local copy of institutional configs are available when running the pipeline.
So using `-profile <NAME>` should work if available within [nf-core/configs](https://github.com/nf-core/configs).

You can run the pipeline by simply providing the directory path for the `workflow` folder.
Note that if using Singularity, you will also need to provide the path to the Singularity image.
For example:

```bash
nextflow run /path/to/nf-core-methylseq-1.4/workflow/ \
     -profile singularity \
     -with-singularity /path/to/nf-core-methylseq-1.4/singularity-images/nf-core-methylseq-1.4.simg \
     # .. other normal pipeline parameters from here on..
     --input '*_R{1,2}.fastq.gz' --genome GRCh38
```

## Pipeline software licences

Sometimes it's useful to see the software licences of the tools used in a pipeline. You can use the `licences` subcommand to fetch and print the software licence from each conda / PyPI package used in an nf-core pipeline.

```console
$ nf-core licences rnaseq

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10

  INFO     Fetching licence information for 25 tools
  INFO     Warning: This tool only prints licence information for the software tools packaged using conda.
  INFO     The pipeline may use other software and dependencies not described here.
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Package Name                      ┃ Version ┃ Licence              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ stringtie                         │ 2.0     │ Artistic License 2.0 │
│ bioconductor-summarizedexperiment │ 1.14.0  │ Artistic-2.0         │
│ preseq                            │ 2.0.3   │ GPL                  │
│ trim-galore                       │ 0.6.4   │ GPL                  │
│ bioconductor-edger                │ 3.26.5  │ GPL >=2              │
│ fastqc                            │ 0.11.8  │ GPL >=3              │
│ bioconductor-tximeta              │ 1.2.2   │ GPLv2                │
│ qualimap                          │ 2.2.2c  │ GPLv2                │
│ r-gplots                          │ 3.0.1.1 │ GPLv2                │
│ r-markdown                        │ 1.1     │ GPLv2                │
│ rseqc                             │ 3.0.1   │ GPLv2                │
│ bioconductor-dupradar             │ 1.14.0  │ GPLv3                │
│ deeptools                         │ 3.3.1   │ GPLv3                │
│ hisat2                            │ 2.1.0   │ GPLv3                │
│ multiqc                           │ 1.7     │ GPLv3                │
│ salmon                            │ 0.14.2  │ GPLv3                │
│ star                              │ 2.6.1d  │ GPLv3                │
│ subread                           │ 1.6.4   │ GPLv3                │
│ r-base                            │ 3.6.1   │ GPLv3.0              │
│ sortmerna                         │ 2.1b    │ LGPL                 │
│ gffread                           │ 0.11.4  │ MIT                  │
│ picard                            │ 2.21.1  │ MIT                  │
│ samtools                          │ 1.9     │ MIT                  │
│ r-data.table                      │ 1.12.4  │ MPL-2.0              │
│ matplotlib                        │ 3.0.3   │ PSF-based            │
└───────────────────────────────────┴─────────┴──────────────────────┘
```

## Creating a new workflow

The `create` subcommand makes a new workflow using the nf-core base template.
With a given pipeline name, description and author, it makes a starter pipeline which follows nf-core best practices.

After creating the files, the command initialises the folder as a git repository and makes an initial commit. This first "vanilla" commit which is identical to the output from the templating tool is important, as it allows us to keep your pipeline in sync with the base template in the future.
See the [nf-core syncing docs](https://nf-co.re/developers/sync) for more information.

```console
$ nf-core create

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10

Workflow Name: nextbigthing
Description: This pipeline analyses data from the next big 'omics technique
Author: Big Steve
  INFO     Creating new nf-core pipeline: nf-core/nextbigthing
  INFO     Initialising pipeline git repository
  INFO     Done. Remember to add a remote and push to GitHub:
            cd /Users/philewels/GitHub/nf-core/tools/test-create/nf-core-nextbigthing
            git remote add origin git@github.com:USERNAME/REPO_NAME.git
            git push --all origin
  INFO     This will also push your newly created dev branch and the TEMPLATE branch for syncing.
  INFO     !!!!!! IMPORTANT !!!!!!

           If you are interested in adding your pipeline to the nf-core community,
           PLEASE COME AND TALK TO US IN THE NF-CORE SLACK BEFORE WRITING ANY CODE!

           Please read: https://nf-co.re/developers/adding_pipelines#join-the-community
```

Once you have run the command, create a new empty repository on GitHub under your username (not the `nf-core` organisation, yet) and push the commits from your computer using the example commands in the above log.
You can then continue to edit, commit and push normally as you build your pipeline.

Please see the [nf-core documentation](https://nf-co.re/developers/adding_pipelines) for a full walkthrough of how to create a new nf-core workflow.

Note that if the required arguments for `nf-core create` are not given, it will interactively prompt for them. If you prefer, you can supply them as command line arguments. See `nf-core create --help` for more information.

## Linting a workflow

The `lint` subcommand checks a given pipeline for all nf-core community guidelines.
This is the same test that is used on the automated continuous integration tests.

For example, the current version looks something like this:

```console
$ cd path/to/my_pipeline
$ nf-core lint .

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'
    nf-core/tools version 1.10.dev0


  INFO     Testing pipeline: nf-core-testpipeline/
╭──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ [!] 3 Test Warnings                                                                                      │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ https://nf-co.re/errors#5: GitHub Actions AWS full test should test full datasets: nf-core-testpipeline… │
│ https://nf-co.re/errors#8: Conda dep outdated: bioconda::fastqc=0.11.8, 0.11.9 available                 │
│ https://nf-co.re/errors#8: Conda dep outdated: bioconda::multiqc=1.7, 1.9 available                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭───────────────────────╮
│ LINT RESULTS SUMMARY  │
├───────────────────────┤
│ [✔] 117 Tests Passed  │
│ [!]   3 Test Warnings │
│ [✗]   0 Test Failed   │
╰───────────────────────╯
```

You can find extensive documentation about each of the lint tests in the [lint errors documentation](https://nf-co.re/errors).

## Working with pipeline schema

nf-core pipelines have a `nextflow_schema.json` file in their root which describes the different parameters used by the workflow.
These files allow automated validation of inputs when running the pipeline, are used to generate command line help and can be used to build interfaces to launch pipelines.
Pipeline schema files are built according to the [JSONSchema specification](https://json-schema.org/) (Draft 7).

To help developers working with pipeline schema, nf-core tools has three `schema` sub-commands:

* `nf-core schema validate`
* `nf-core schema build`
* `nf-core schema lint`

### nf-core schema validate

Nextflow can take input parameters in a JSON or YAML file when running a pipeline using the `-params-file` option.
This command validates such a file against the pipeline schema.

Usage is `nextflow schema validate <pipeline> --params <parameter file>`, eg:

```console
$ nf-core schema validate my_pipeline --params my_inputs.json

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10

  INFO     [✓] Pipeline schema looks valid (found 26 params)
  ERROR    [✗] Input parameters are invalid: 'input' is a required property
```

The `pipeline` option can be a directory containing a pipeline, a path to a schema file or the name of an nf-core pipeline (which will be downloaded using `nextflow pull`).

### nf-core schema build

Manually building JSONSchema documents is not trivial and can be very error prone.
Instead, the `nf-core schema build` command collects your pipeline parameters and gives interactive prompts about any missing or unexpected params.
If no existing schema is found it will create one for you.

Once built, the tool can send the schema to the nf-core website so that you can use a graphical interface to organise and fill in the schema.
The tool checks the status of your schema on the website and once complete, saves your changes locally.

Usage is `nextflow schema build <pipeline_directory>`, eg:

```console
$ nf-core schema build nf-core-testpipeline

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10

  INFO     [✓] Pipeline schema looks valid (found 25 params)                                                                                                      schema.py:82
❓ Unrecognised 'params.old_param' found in schema but not pipeline! Remove it? [y/n]: y
❓ Unrecognised 'params.we_removed_this_too' found in schema but not pipeline! Remove it? [y/n]: y
✨ Found 'params.input' in pipeline but not in schema. Add to pipeline schema? [y/n]: y
✨ Found 'params.outdir' in pipeline but not in schema. Add to pipeline schema? [y/n]: y
  INFO     Writing schema with 25 params: 'nf-core-testpipeline/nextflow_schema.json'                                                                            schema.py:121
🚀 Launch web builder for customisation and editing? [y/n]: y
  INFO: Opening URL: https://nf-co.re/pipeline_schema_builder?id=1234567890_abc123def456
  INFO: Waiting for form to be completed in the browser. Remember to click Finished when you're done.
  INFO: Found saved status from nf-core JSON Schema builder
  INFO: Writing JSON schema with 25 params: nf-core-testpipeline/nextflow_schema.json
```

There are three flags that you can use with this command:

* `--no-prompts`: Make changes without prompting for confirmation each time. Does not launch web tool.
* `--web-only`: Skips comparison of the schema against the pipeline parameters and only launches the web tool.
* `--url <web_address>`: Supply a custom URL for the online tool. Useful when testing locally.

### nf-core schema lint

The pipeline schema is linted as part of the main `nf-core lint` command,
however sometimes it can be useful to quickly check the syntax of the JSONSchema without running a full lint run.

Usage is `nextflow schema lint <schema>`, eg:

```console
$ nf-core schema lint nextflow_schema.json

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10

  ERROR    [✗] Pipeline schema does not follow nf-core specs:
            Definition subschema 'input_output_options' not included in schema 'allOf'
```

## Bumping a pipeline version number

When releasing a new version of a nf-core pipeline, version numbers have to be updated in several different places. The helper command `nf-core bump-version` automates this for you to avoid manual errors (and frustration!).

The command uses results from the linting process, so will only work with workflows that pass these tests.

Usage is `nf-core bump-version <pipeline_dir> <new_version>`, eg:

```console
$ cd path/to/my_pipeline
$ nf-core bump-version . 1.0

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10

INFO     Running nf-core lint tests
INFO     Testing pipeline: nf-core-testpipeline/
INFO     Changing version number:
           Current version number is '1.4'
           New version number will be '1.5'
INFO     Updating version in nextflow.config
          - version = '1.4'
          + version = '1.5'
INFO     Updating version in nextflow.config
          - process.container = 'nfcore/testpipeline:1.4'
          + process.container = 'nfcore/testpipeline:1.5'
INFO     Updating version in .github/workflows/ci.yml
          - run: docker build --no-cache . -t nfcore/testpipeline:1.4
          + run: docker build --no-cache . -t nfcore/testpipeline:1.5
INFO     Updating version in .github/workflows/ci.yml
          - docker tag nfcore/testpipeline:dev nfcore/testpipeline:1.4
          + docker tag nfcore/testpipeline:dev nfcore/testpipeline:1.5
INFO     Updating version in environment.yml
          - name: nf-core-testpipeline-1.4
          + name: nf-core-testpipeline-1.5
INFO     Updating version in Dockerfile
          - ENV PATH /opt/conda/envs/nf-core-testpipeline-1.4/bin:$PATH
          - RUN conda env export --name nf-core-testpipeline-1.4 > nf-core-testpipeline-1.4.yml
          + ENV PATH /opt/conda/envs/nf-core-testpipeline-1.5/bin:$PATH
          + RUN conda env export --name nf-core-testpipeline-1.5 > nf-core-testpipeline-1.5.yml
```

To change the required version of Nextflow instead of the pipeline version number, use the flag `--nextflow`.

To export the lint results to a JSON file, use `--json [filename]`. For markdown, use `--markdown [filename]`.

As linting tests can give a pass state for CI but with warnings that need some effort to track down, the linting
code attempts to post a comment to the GitHub pull-request with a summary of results if possible.
It does this when the environment variables `GITHUB_COMMENTS_URL` and `GITHUB_TOKEN` are set and if there are
any failing or warning tests. If a pull-request is updated with new commits, the original comment will be
updated with the latest results instead of posting lots of new comments for each `git push`.

A typical GitHub Actions step with the required environment variables may look like this (will only work on pull-request events):

```yaml
- name: Run nf-core lint
  env:
    GITHUB_COMMENTS_URL: ${{ github.event.pull_request.comments_url }}
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    GITHUB_PR_COMMIT: ${{ github.event.pull_request.head.sha }}
  run: nf-core lint $GITHUB_WORKSPACE
```

## Sync a pipeline with the template

Over time, the main nf-core pipeline template is updated. To keep all nf-core pipelines up to date,
we synchronise these updates automatically when new versions of nf-core/tools are released.
This is done by maintaining a special `TEMPLATE` branch, containing a vanilla copy of the nf-core template
with only the variables used when it first ran (name, description etc.). This branch is updated and a
pull-request can be made with just the updates from the main template code.

This command takes a pipeline directory and attempts to run this synchronisation.
Usage is `nf-core sync <pipeline_dir>`, eg:

```console
$ nf-core sync my_pipeline/

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10

INFO     Pipeline directory: /path/to/my_pipeline
INFO     Fetching workflow config variables
INFO     Deleting all files in TEMPLATE branch
INFO     Making a new template pipeline using pipeline variables
INFO     Committed changes to TEMPLATE branch
INFO     Now try to merge the updates in to your pipeline:
           cd /path/to/my_pipeline
           git merge TEMPLATE
```

The sync command tries to check out the `TEMPLATE` branch from the `origin` remote
or an existing local branch called `TEMPLATE`. It will fail if it cannot do either
of these things. The `nf-core create` command should make this template automatically
when you first start your pipeline. Please see the
[nf-core website sync documentation](https://nf-co.re/developers/sync) if you have difficulties.

By default, the tool will collect workflow variables from the current branch in your
pipeline directory. You can supply the `--from-branch` flag to specific a different branch.

Finally, if you give the `--pull-request` flag, the command will push any changes to the remote
and attempt to create a pull request using the GitHub API. The GitHub username and repository
name will be fetched from the remote url (see `git remote -v | grep origin`), or can be supplied
with `--username` and `--repository`.

To create the pull request, a personal access token is required for API authentication.
These can be created at [https://github.com/settings/tokens](https://github.com/settings/tokens).
Supply this using the `--auth-token` flag.

Finally, if `--all` is supplied, then the command attempts to pull and synchronise all nf-core workflows.
This is used by the nf-core/tools release automation to synchronise all nf-core pipelines
with the newest version of the template. It requires authentication as either the nf-core-bot account
or as an nf-core administrator.

```console
$ nf-core sync --all

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 1.10

INFO     Syncing nf-core/ampliseq
[...]
INFO     Successfully synchronised [n] pipelines
```

## Citation

If you use `nf-core tools` in your work, please cite the `nf-core` publication as follows:

> **The nf-core framework for community-curated bioinformatics pipelines.**
>
> Philip Ewels, Alexander Peltzer, Sven Fillinger, Harshil Patel, Johannes Alneberg, Andreas Wilm, Maxime Ulysse Garcia, Paolo Di Tommaso & Sven Nahnsen.
>
> _Nat Biotechnol._ 2020 Feb 13. doi: [10.1038/s41587-020-0439-x](https://dx.doi.org/10.1038/s41587-020-0439-x).
