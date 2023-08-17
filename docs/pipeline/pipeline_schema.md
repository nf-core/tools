---
title: Pipeline schema
description: JSON schema based pipeline parameter validation and documentation
weight: 80
section: pipelines
---

# Introduction

nf-core pipelines have a `nextflow_schema.json` file in their root which describes the different parameters used by the workflow.
These files allow automated validation of inputs when running the pipeline, are used to generate command line help and can be used to build interfaces to launch pipelines.
Pipeline schema files are built according to the [JSONSchema specification](https://json-schema.org/) (Draft 7).

To help developers working with pipeline schema, nf-core tools has three `schema` sub-commands:

- `nf-core schema validate`
- `nf-core schema build`
- `nf-core schema docs`
- `nf-core schema lint`

## Validate pipeline parameters

Nextflow can take input parameters in a JSON or YAML file when running a pipeline using the `-params-file` option.
This command validates such a file against the pipeline schema.

Usage is `nf-core schema validate <pipeline> <parameter file>`. eg with the pipeline downloaded [above](#download-pipeline), you can run:

<!-- RICH-CODEX
working_dir: tmp
before_command: 'echo "{input: myfiles.csv, outdir: results}" > nf-params.json'
timeout: 10
after_command: rm nf-params.json
-->

![`nf-core schema validate nf-core-rnaseq/3_8 nf-params.json`](../images/nf-core-schema-validate.svg)

The `pipeline` option can be a directory containing a pipeline, a path to a schema file or the name of an nf-core pipeline (which will be downloaded using `nextflow pull`).

## Build a pipeline schema

Manually building JSONSchema documents is not trivial and can be very error prone.
Instead, the `nf-core schema build` command collects your pipeline parameters and gives interactive prompts about any missing or unexpected params.
If no existing schema is found it will create one for you.

Once built, the tool can send the schema to the nf-core website so that you can use a graphical interface to organise and fill in the schema.
The tool checks the status of your schema on the website and once complete, saves your changes locally.

Usage is `nf-core schema build -d <pipeline_directory>`, eg:

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
timeout: 10
before_command: sed '25,30d' nextflow_schema.json > nextflow_schema.json.tmp && mv nextflow_schema.json.tmp nextflow_schema.json
-->

![`nf-core schema build --no-prompts`](../images/nf-core-schema-build.svg)

There are four flags that you can use with this command:

- `--dir <pipeline_dir>`: Specify a pipeline directory other than the current working directory
- `--no-prompts`: Make changes without prompting for confirmation each time. Does not launch web tool.
- `--web-only`: Skips comparison of the schema against the pipeline parameters and only launches the web tool.
- `--url <web_address>`: Supply a custom URL for the online tool. Useful when testing locally.

## Display the documentation for a pipeline schema

To get an impression about the current pipeline schema you can display the content of the `nextflow_schema.json` with `nf-core schema docs <pipeline-schema>`. This will print the content of your schema in Markdown format to the standard output.

There are four flags that you can use with this command:

- `--output <filename>`: Output filename. Defaults to standard out.
- `--format [markdown|html]`: Format to output docs in.
- `--force`: Overwrite existing files
- `--columns <columns_list>`: CSV list of columns to include in the parameter tables

## Add new parameters to the pipeline schema

If you want to add a parameter to the schema, you first have to add the parameter and its default value to the `nextflow.config` file with the `params` scope. Afterwards, you run the command `nf-core schema build` to add the parameters to your schema and open the graphical interface to easily modify the schema.

The graphical interface is oganzised in groups and within the groups the single parameters are stored. For a better overview you can collapse all groups with the `Collapse groups` button, then your new parameters will be the only remaining one at the bottom of the page. Now you can either create a new group with the `Add group` button or drag and drop the paramters in an existing group. Therefor the group has to be expanded. The group title will be displayed, if you run your pipeline with the `--help` flag and its description apears on the parameter page of your pipeline.

Now you can start to change the parameter itself. The `ID` of a new parameter should be defined in small letters without whitespaces. The description is a short free text explanation about the parameter, that appears if you run your pipeline with the `--help` flag. By clicking on the dictionary icon you can add a longer explanation for the parameter page of your pipeline. Usually, they contain a small paragraph about the parameter settings or a used datasource, like databases or references. If you want to specify some conditions for your parameter, like the file extension, you can use the nut icon to open the settings. This menu depends on the `type` you assigned to your parameter. For integers you can define a min and max value, and for strings the file extension can be specified.

The `type` field is one of the most important points in your pipeline schema, since it defines the datatype of your input and how it will be interpreted. This allows extensive testing prior to starting the pipeline.

The basic datatypes for a pipeline schema are:

- `string`
- `number`
- `integer`
- `boolean`

For the `string` type you have three different options in the settings (nut icon): `enumerated values`, `pattern` and `format`. The first option, `enumerated values`, allows you to specify a list of specific input values. The list has to be separated with a pipe. The `pattern` and `format` settings can depend on each other. The `format` has to be either a directory or a file path. Depending on the `format` setting selected, specifying the `pattern` setting can be the most efficient and time saving option, especially for `file paths`. The `number` and `integer` types share the same settings. Similarly to `string`, there is an `enumerated values` option with the possibility of specifying a `min` and `max` value. For the `boolean` there is no further settings and the default value is usually `false`. The `boolean` value can be switched to `true` by adding the flag to the command. This parameter type is often used to skip specific sections of a pipeline.

After filling the schema, click on the `Finished` button in the top right corner, this will automatically update your `nextflow_schema.json`. If this is not working, the schema can be copied from the graphical interface and pasted in your `nextflow_schema.json` file.

## Update existing pipeline schema

It's important to change the default value of a parameter in the `nextflow.config` file first and then in the pipeline schema, because the value in the config file overwrites the value in the pipeline schema. To change any other parameter use `nf-core schema build --web-only` to open the graphical interface without rebuilding the pipeline schema. Now, the parameters can be changed as mentioned above but keep in mind that changing the parameter datatype depends on the default value specified in the `nextflow.config` file.

## Linting a pipeline schema

The pipeline schema is linted as part of the main pipeline `nf-core lint` command,
however sometimes it can be useful to quickly check the syntax of the JSONSchema without running a full lint run.

Usage is `nf-core schema lint <schema>` (defaulting to `nextflow_schema.json`), eg:

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
-->

![`nf-core schema lint`](../images/nf-core-schema-lint.svg)
