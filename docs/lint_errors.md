# Linting Errors

This page contains detailed descriptions of the tests done by the [nf-core/tools](https://github.com/nf-core/tools) package. Linting errors should show URLs next to any failures that link to the relevant heading below.

## Error #1 - File not found / must be removed ## {#1}

nf-core pipelines should adhere to a common file structure for consistency.

The lint test looks for the following required files:

* `nextflow.config`
  * The main nextflow config file
* `Dockerfile`
  * A docker build script to generate a docker image with the required software
* Continuous integration tests with [GitHub Actions](https://github.com/features/actions)
  * GitHub Actions workflows for CI of your pipeline (`.github/workflows/ci.yml`), branch protection (`.github/workflows/branch.yml`) and nf-core best practice linting (`.github/workflows/linting.yml`)
* `LICENSE`, `LICENSE.md`, `LICENCE.md` or `LICENCE.md`
  * The MIT licence. Copy from [here](https://raw.githubusercontent.com/nf-core/tools/master/LICENSE).
* `README.md`
  * A well written readme file in markdown format
* `CHANGELOG.md`
  * A markdown file listing the changes for each pipeline release
* `docs/README.md`, `docs/output.md` and `docs/usage.md`
  * A `docs` directory with an index `README.md`, usage and output documentation

The following files are suggested but not a hard requirement. If they are missing they trigger a warning:

* `main.nf`
  * It's recommended that the main workflow script is called `main.nf`
* `conf/base.config`
  * A `conf` directory with at least one config called `base.config`

Additionally, the following files must not be present:

* `Singularity`

## Error #2 - Docker file check failed ## {#2}

Pipelines should have a files called `Dockerfile` in their root directory.
The file is used for automated docker image builds. This test checks that the file
exists and contains at least the string `FROM` (`Dockerfile`).

## Error #3 - Licence check failed ## {#3}

nf-core pipelines must ship with an open source [MIT licence](https://choosealicense.com/licenses/mit/).

This test fails if the following conditions are not met:

* No licence file found
  * `LICENSE`, `LICENSE.md`, `LICENCE.md` or `LICENCE.md`
* Licence file contains fewer than 4 lines of text
* File does not contain the string `without restriction`
* Licence contains template placeholders
  * `[year]`, `[fullname]`, `<YEAR>`, `<COPYRIGHT HOLDER>`, `<year>` or `<copyright holders>`

## Error #4 - Nextflow config check failed ## {#4}

nf-core pipelines are required to be configured with a minimal set of variable
names. This test fails or throws warnings if required variables are not set.

> **Note:** These config variables must be set in `nextflow.config` or another config
> file imported from there. Any variables set in nextflow script files (eg. `main.nf`)
> are not checked and will be assumed to be missing.

The following variables fail the test if missing:

* `params.outdir`
  * A directory in which all pipeline results should be saved
* `manifest.name`
  * The pipeline name. Should begin with `nf-core/`
* `manifest.description`
  * A description of the pipeline
* `manifest.version`
  * The version of this pipeline. This should correspond to a [GitHub release](https://help.github.com/articles/creating-releases/).
* `manifest.nextflowVersion`
  * The minimum version of Nextflow required to run the pipeline.
  * Should `>=` a version number, eg. `manifest.nextflowVersion = '>=0.31.0'` (check the [Nexftlow documentation](https://www.nextflow.io/docs/latest/config.html#scope-manifest) for more.)
* `manifest.homePage`
  * The homepage for the pipeline. Should be the nf-core GitHub repository URL,
    so beginning with `https://github.com/nf-core/`
* `timeline.enabled`, `trace.enabled`, `report.enabled`, `dag.enabled`
  * The nextflow timeline, trace, report and DAG should be enabled by default
* `process.cpus`, `process.memory`, `process.time`
  * Default CPUs, memory and time limits for tasks

The following variables throw warnings if missing:

* `manifest.mainScript`
  * The filename of the main pipeline script (recommended to be `main.nf`)
* `timeline.file`, `trace.file`, `report.file`, `dag.file`
  * Default filenames for the timeline, trace and report
  * Should be set to a results folder, eg: `${params.outdir}/pipeline_info/trace.[workflowname].txt"`
  * The DAG file path should end with `.svg`
    * If Graphviz is not installed, Nextflow will generate a `.dot` file instead
* `process.container`
  * Dockerhub handle for a single default container for use by all processes.
  * Must specify a tag that matches the pipeline version number if set.
  * If the pipeline version number contains the string `dev`, the dockerhub tag must be `:dev`
* `params.reads`
  * Input parameter to specify input data (typically FastQ files / pairs)
* `params.single_end`
  * Specify to work with single-end sequence data instead of paired-end by default
  * Nextflow implementation: `.fromFilePairs( params.reads, size: params.single_end ? 1 : 2 )`

The following variables are depreciated and fail the test if they are still present:

* `params.version`
  * The old method for specifying the pipeline version. Replaced by `manifest.version`
* `params.nf_required_version`
  * The old method for specifying the minimum Nextflow version. Replaced by `manifest.nextflowVersion`
* `params.container`
  * The old method for specifying the dockerhub container address. Replaced by `process.container`
* `singleEnd` and `igenomesIgnore`
  * Changed to `single_end` and `igenomes_ignore`
  * The `snake_case` convention should now be used when defining pipeline parameters

## Error #5 - Continuous Integration configuration ## {#5}

nf-core pipelines must have CI testing with GitHub Actions.

### GitHub Actions

There are 3 main GitHub Actions CI test files: `ci.yml`, `linting.yml` and `branch.yml` and they can all be found in the `.github/workflows/` directory.  

This test will fail if the following requirements are not met in these files:  

1. `ci.yml`: Contains all the commands required to test the pipeline  
    * Must be turned on for `push` and `pull_request`.  
    * The minimum Nextflow version specified in the pipeline's `nextflow.config` has to match that defined by `nxf_ver` in this file:  

      ```yaml
      jobs:
      test:
          runs-on: ubuntu-18.04
          strategy:
              matrix:
                  # Nextflow versions: check pipeline minimum and current latest
                  nxf_ver: ['19.10.0', '']
      ```

    * The `Docker` container for the pipeline must be tagged appropriately for:  
        * Development pipelines: `docker tag nfcore/<pipeline_name>:dev nfcore/<pipeline_name>:dev`  
        * Released pipelines: `docker tag nfcore/<pipeline_name>:dev nfcore/<pipeline_name>:<tag>`  

      ```yaml
      jobs:
      test:
          runs-on: ubuntu-18.04
          steps:
          - name: Pull image
              run: |
              docker pull nfcore/<pipeline_name>:dev
              docker tag nfcore/<pipeline_name>:dev nfcore/<pipeline_name>:1.0.0
      ```

2. `linting.yml`: Specifies the commands to lint the pipeline repository using `nf-core lint` and `markdownlint`  
    * Must be turned on for `push` and `pull_request`.  
    * Must have the command `nf-core lint ${GITHUB_WORKSPACE}`.  
    * Must have the command `markdownlint ${GITHUB_WORKSPACE} -c ${GITHUB_WORKSPACE}/.github/markdownlint.yml`.  

3. `branch.yml`: Ensures that pull requests to the protected `master` branch are coming from the correct branch  
    * Must be turned on for `pull_request` to `master`.  
    * Checks that PRs to the protected `master` branch can only come from an nf-core `dev` branch or a fork `patch` branch:  

    ```yaml
    jobs:
    test:
    runs-on: ubuntu-18.04
    steps:
      # PRs are only ok if coming from an nf-core `dev` branch or a fork `patch` branch
      - name: Check PRs
        run: |
          { [[ $(git remote get-url origin) == *nf-core/<pipeline_name> ]] && [[ ${GITHUB_HEAD_REF} = "dev" ]]; } || [[ ${GITHUB_HEAD_REF} == "patch" ]]
    ```

## Error #6 - Repository `README.md` tests ## {#6}

The `README.md` files for a project are very important and must meet some requirements:

* Nextflow badge
  * If no Nextflow badge is found, a warning is given
  * If a badge is found but the version doesn't match the minimum version in the config file, the test fails
  * Example badge code:

    ```markdown
    [![Nextflow](https://img.shields.io/badge/nextflow-%E2%89%A50.27.6-brightgreen.svg)](https://www.nextflow.io/)
    ```

* Bioconda badge
  * If your pipeline contains a file called `environment.yml`, a bioconda badge is required
  * Required badge code:

    ```markdown
    [![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](http://bioconda.github.io/)
    ```

## Error #7 - Pipeline and container version numbers ## {#7}

> This test only runs when `--release` is set

These tests look at `process.container` and `$GITHUB_REF` only if they are set.

* Container name must have a tag specified (eg. `nfcore/pipeline:version`)

## Error #8 - Conda environment tests ## {#8}

> These tests only run when your pipeline has a root file called `environment.yml`

* The environment `name` must match the pipeline name and version
  * The pipeline name is defined in the config variable `manifest.name`
  * Replace the slash with a hyphen as environment names shouldn't contain that character
  * Example: For `nf-core/test` version 1.4, the conda environment name should be `nf-core-test-1.4`

Each dependency is checked using the [Anaconda API service](https://api.anaconda.org/docs).
Dependency sublists are ignored with the exception of `- pip`: these packages are also checked
for pinned version numbers and checked using the [PyPI JSON API](https://wiki.python.org/moin/PyPIJSON).

Note that conda dependencies with pinned channels (eg. `conda-forge::openjdk`) are fine
and should be handled by the linting properly.

Each dependency can have the following lint failures and warnings:

* (Test failure) Dependency does not have a pinned version number, eg. `toolname=1.6.8`
* (Test failure) The package cannot be found on any of the listed conda channels (or PyPI if `pip`)
* (Test failure) The package version cannot be found on anaconda cloud (or on PyPi, for `pip` dependencies)
* (Test warning) A newer version of the package is available

> NB: Conda package versions should be pinned with one equals sign (`toolname=1.1`), pip with two (`toolname==1.2`)

## Error #9 - Dockerfile for use with Conda environments ## {#9}

> This test only runs if there is both `environment.yml`
> and `Dockerfile` present in the workflow.

If a workflow has a conda `environment.yml` file (see above), the `Dockerfile` should use this
to create the container. Such `Dockerfile`s can usually be very short, eg:

```Dockerfile
FROM nfcore/base:1.7
MAINTAINER Rocky Balboa <your@email.com>
LABEL authors="your@email.com" \
    description="Docker image containing all requirements for the nf-core mypipeline pipeline"

COPY environment.yml /
RUN conda env create -f /environment.yml && conda clean -a
RUN conda env export --name nf-core-mypipeline-1.0 > nf-core-mypipeline-1.0.yml
ENV PATH /opt/conda/envs/nf-core-mypipeline-1.0/bin:$PATH
```

To enforce this minimal `Dockerfile` and check for common copy+paste errors, we require
that the above template is used.
Failures are generated if the `FROM`, `COPY` and `RUN` statements above are not present.
These lines must be an exact copy of the above example.

Note that the base `nfcore/base` image should be tagged to the most recent release.
The linting tool compares the tag against the currently installed version.

Additional lines and different metadata can be added without causing the test to fail.

## Error #10 - Template TODO statement found ## {#10}

The nf-core workflow template contains a number of comment lines with the following format:

```groovy
// TODO nf-core: Make some kind of change to the workflow here
```

This lint test runs through all files in the pipeline and searches for these lines.

## Error #11 - Singularity file found ##{#11}

As we are relying on [Docker Hub](https://https://hub.docker.com/) instead of Singularity and all containers are automatically pulled from there, repositories should not have a `Singularity` file present.

## Error #12 - Pipeline name ## {#12}

In order to ensure consistent naming, pipeline names should contain only lower case, alphabetical characters. Otherwise a warning is displayed.
