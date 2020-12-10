# Linting Errors

This page contains detailed descriptions of the tests done by the [nf-core/tools](https://github.com/nf-core/tools) package. Linting errors should show URLs next to any failures that link to the relevant heading below.

## Error #1 - File not found / must be removed ## {#1}

nf-core pipelines should adhere to a common file structure for consistency.

The lint test looks for the following required files:

* `nextflow.config`
  * The main nextflow config file
* `nextflow_schema.json`
  * A JSON schema describing pipeline parameters, generated using `nf-core schema build`
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
* `environment.yml`
  * A conda environment file describing the required software
* `Dockerfile`
  * A docker build script to generate a docker image with the required software
* `conf/base.config`
  * A `conf` directory with at least one config called `base.config`
* `.github/workflows/awstest.yml` and `.github/workflows/awsfulltest.yml`
  * GitHub workflow scripts used for automated tests on AWS

The following files will cause a failure if the _are_ present (to fix, delete them):

* `Singularity`
  * As we are relying on [Docker Hub](https://https://hub.docker.com/) instead of Singularity
    and all containers are automatically pulled from there, repositories should not
    have a `Singularity` file present.
* `parameters.settings.json`
  * The syntax for pipeline schema has changed - old `parameters.settings.json` should be
    deleted and new `nextflow_schema.json` files created instead.
* `bin/markdown_to_html.r`
  * The old markdown to HTML conversion script, now replaced by `markdown_to_html.py`
* `.github/workflows/push_dockerhub.yml`
  * The old dockerhub build script, now split into `.github/workflows/push_dockerhub_dev.yml` and `.github/workflows/push_dockerhub_release.yml`

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
  * If `--release` is set when running `nf-core lint`, the version number must not contain the string `dev`
  * If `--release` is _not_ set, the version should end in `dev` (warning triggered if not)
* `manifest.nextflowVersion`
  * The minimum version of Nextflow required to run the pipeline.
  * Should be `>=` or `!>=` and a version number, eg. `manifest.nextflowVersion = '>=0.31.0'` (see [Nextflow documentation](https://www.nextflow.io/docs/latest/config.html#scope-manifest))
  * `>=` warns about old versions but tries to run anyway, `!>=` fails for old versions. Only use the latter if you _know_ that the pipeline will certainly fail before this version.
  * This should correspond to the `NXF_VER` version tested by GitHub Actions.
* `manifest.homePage`
  * The homepage for the pipeline. Should be the nf-core GitHub repository URL,
    so beginning with `https://github.com/nf-core/`
* `timeline.enabled`, `trace.enabled`, `report.enabled`, `dag.enabled`
  * The nextflow timeline, trace, report and DAG should be enabled by default (set to `true`)
* `process.cpus`, `process.memory`, `process.time`
  * Default CPUs, memory and time limits for tasks
* `params.input`
  * Input parameter to specify input data, specify this to avoid a warning
  * Typical usage:
    * `params.input`: Input data that is not NGS sequencing data

The following variables throw warnings if missing:

* `manifest.mainScript`
  * The filename of the main pipeline script (recommended to be `main.nf`)
* `timeline.file`, `trace.file`, `report.file`, `dag.file`
  * Default filenames for the timeline, trace and report
  * Should be set to a results folder, eg: `${params.outdir}/pipeline_info/trace.[workflowname].txt"`
  * The DAG file path should end with `.svg`
    * If Graphviz is not installed, Nextflow will generate a `.dot` file instead
* `process.container`
  * Docker Hub handle for a single default container for use by all processes.
  * Must specify a tag that matches the pipeline version number if set.
  * If the pipeline version number contains the string `dev`, the DockerHub tag must be `:dev`

The following variables are depreciated and fail the test if they are still present:

* `params.version`
  * The old method for specifying the pipeline version. Replaced by `manifest.version`
* `params.nf_required_version`
  * The old method for specifying the minimum Nextflow version. Replaced by `manifest.nextflowVersion`
* `params.container`
  * The old method for specifying the dockerhub container address. Replaced by `process.container`
* `igenomesIgnore`
  * Changed to `igenomes_ignore`
  * The `snake_case` convention should now be used when defining pipeline parameters

Process-level configuration syntax is checked and fails if uses the old Nextflow syntax, for example:
`process.$fastqc` instead of `process withName:'fastqc'`.

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
    [![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](https://bioconda.github.io/)
    ```

## Error #7 - Pipeline and container version numbers ## {#7}

> This test only runs when `--release` is set or `$GITHUB_REF` is equal to `master`

These tests look at `process.container` and `$GITHUB_REF` only if they are set.

* Container name must have a tag specified (eg. `nfcore/pipeline:version`)
* Container tag / `$GITHUB_REF` must contain only numbers and dots
* Tags and `$GITHUB_REF` must all match one another

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

## Error #10 - Template TODO statement found ## {#10}

The nf-core workflow template contains a number of comment lines with the following format:

```groovy
// TODO nf-core: Make some kind of change to the workflow here
```

This lint test runs through all files in the pipeline and searches for these lines.

## Error #11 - Pipeline name ## {#11}

_..removed.._

## Error #12 - Pipeline name ## {#12}

In order to ensure consistent naming, pipeline names should contain only lower case, alphanumeric characters. Otherwise a warning is displayed.

## Error #13 - Pipeline name ## {#13}

The `nf-core create` pipeline template uses [cookiecutter](https://github.com/cookiecutter/cookiecutter) behind the scenes.
This check fails if any cookiecutter template variables such as `{{ cookiecutter.pipeline_name }}` are fouund in your pipeline code.
Finding a placeholder like this means that something was probably copied and pasted from the template without being properly rendered for your pipeline.

## Error #14 - Pipeline schema syntax ## {#14}

Pipelines should have a `nextflow_schema.json` file that describes the different pipeline parameters (eg. `params.something`, `--something`).

* Schema should be valid JSON files
* Schema should adhere to [JSONSchema](https://json-schema.org/), Draft 7.
* Parameters can be described in two places:
  * As `properties` in the top-level schema object
  * As `properties` within subschemas listed in a top-level `definitions` objects
* The schema must describe at least one parameter
* There must be no duplicate parameter IDs across the schema and definition subschema
* All subschema in `definitions` must be referenced in the top-level `allOf` key
* The top-level `allOf` key must not describe any non-existent definitions
* Core top-level schema attributes should exist and be set as follows:
  * `$schema`: `https://json-schema.org/draft-07/schema`
  * `$id`: URL to the raw schema file, eg. `https://raw.githubusercontent.com/YOURPIPELINE/master/nextflow_schema.json`
  * `title`: `YOURPIPELINE pipeline parameters`
  * `description`: The piepline config `manifest.description`

For example, an _extremely_ minimal schema could look like this:

```json
{
  "$schema": "https://json-schema.org/draft-07/schema",
  "$id": "https://raw.githubusercontent.com/YOURPIPELINE/master/nextflow_schema.json",
  "title": "YOURPIPELINE pipeline parameters",
  "description": "This pipeline is for testing",
  "properties": {
    "first_param": { "type": "string" }
  },
  "definitions": {
    "my_first_group": {
      "properties": {
        "second_param": { "type": "string" }
      }
    }
  },
  "allOf": [{"$ref": "#/definitions/my_first_group"}]
}
```

## Error #15 - Schema config check ## {#15}

The `nextflow_schema.json` pipeline schema should describe every flat parameter returned from the `nextflow config` command (params that are objects or more complex structures are ignored).
Missing parameters result in a lint failure.

If any parameters are found in the schema that were not returned from `nextflow config` a warning is given.
