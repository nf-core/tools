---
title: Create a subworkflows
description: Create a new nf-core subworkflow from the nf-core subworkflow template.
weight: 70
section: subworkflows
---

This command creates a new nf-core subworkflow from the nf-core subworkflow template.
This ensures that your subworkflow follows the nf-core guidelines.
The template contains extensive `TODO` messages to walk you through the changes you need to make to the template.
See the [subworkflow documentation](https://nf-co.re/docs/contributing/subworkflows) for more details around creating a new subworkflow, including rules about nomenclature and a step-by-step guide.

You can create a new subworkflow using `nf-core subworkflows create`.

This command can be used both when writing a subworkflow for the shared [nf-core/modules](https://github.com/nf-core/modules) repository,
and also when creating local subworkflows for a pipeline.

Which type of repository you are working in is detected by the `repository_type` flag in a `.nf-core.yml` file in the root directory,
set to either `pipeline` or `modules`.
The command will automatically look through parent directories for this file to set the root path, so that you can run the command in a subdirectory.
It will start in the current working directory, or whatever is specified with `--dir <directory>`.

The `nf-core subworkflows create` command will prompt you with the relevant questions in order to create all of the necessary subworkflow files.

<!-- RICH-CODEX
working_dir: tmp/modules
fake_command: nf-core subworkflows create bam_stats_samtools --author @nf-core-bot --force
-->

![`nf-core subworkflows create bam_stats_samtools --author @nf-core-bot --force`](../images/nf-core-subworkflows-create.svg)
