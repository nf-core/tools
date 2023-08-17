---
title: Launch a pipeline
description: Provide inputs to a pipeline using a web-based GUI or interactive command-line wizard.
weight: 30
section: pipelines
---

# Introduction

Some nextflow pipelines have a considerable number of command line flags that can be used.
To help with this, you can use the `nf-core launch` command.
You can choose between a web-based graphical interface or an interactive command-line wizard tool to enter the pipeline parameters for your run.
Both interfaces show documentation alongside each parameter and validate your inputs.

The tool uses the `nextflow_schema.json` file from a pipeline to give parameter descriptions, defaults and grouping.
If no file for the pipeline is found, one will be automatically generated at runtime.

Nextflow `params` variables are saved in to a JSON file called `nf-params.json` and used by nextflow with the `-params-file` flag.
This makes it easier to reuse these in the future.

The command takes one argument - either the name of an nf-core pipeline which will be pulled automatically,
or the path to a directory containing a Nextflow pipeline _(can be any pipeline, doesn't have to be nf-core)_.

<!-- RICH-CODEX trim_after: "Command line" -->

![`nf-core launch rnaseq -r 3.8.1`](../images/nf-core-launch-rnaseq.svg)

Once complete, the wizard will ask you if you want to launch the Nextflow run.
If not, you can copy and paste the Nextflow command with the `nf-params.json` file of your inputs.

```console
INFO     [✓] Input parameters look valid
INFO     Nextflow command:
         nextflow run nf-core/rnaseq -params-file "nf-params.json"


Do you want to run this command now?  [y/n]:
```

## Launch tool options

- `-r`, `--revision`
  - Specify a pipeline release (or branch / git commit sha) of the project to run
- `-i`, `--id`
  - You can use the web GUI for nf-core pipelines by clicking _"Launch"_ on the website. Once filled in you will be given an ID to use with this command which is used to retrieve your inputs.
- `-c`, `--command-only`
  - If you prefer not to save your inputs in a JSON file and use `-params-file`, this option will specify all entered params directly in the nextflow command.
- `-p`, `--params-in PATH`
  - To use values entered in a previous pipeline run, you can supply the `nf-params.json` file previously generated.
  - This will overwrite the pipeline schema defaults before the wizard is launched.
- `-o`, `--params-out PATH`
  - Path to save parameters JSON file to. (Default: `nf-params.json`)
- `-a`, `--save-all`
  - Without this option the pipeline will ignore any values that match the pipeline schema defaults.
  - This option saves _all_ parameters found to the JSON file.
- `-h`, `--show-hidden`
  - A pipeline JSON schema can define some parameters as 'hidden' if they are rarely used or for internal pipeline use only.
  - This option forces the wizard to show all parameters, including those labelled as 'hidden'.
- `--url`
  - Change the URL used for the graphical interface, useful for development work on the website.
