# Linting Errors

This page contains detailed descriptions of the tests done by the [nf-core/tools](https://github.com/nf-core/tools) package. Linting errors should show URLs next to any failures that link to the relevant heading below.

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

## Error #10 - Template TODO statement found ## {#10}

The nf-core workflow template contains a number of comment lines with the following format:

```groovy
// TODO nf-core: Make some kind of change to the workflow here
```

This lint test runs through all files in the pipeline and searches for these lines.

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
