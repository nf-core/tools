---
title: Create a module
description: Create a new module from the nf-core module template.
weight: 80
section: modules
---

This command creates a new nf-core module from the nf-core module template.
This ensures that your module follows the nf-core guidelines.
The template contains extensive `TODO` messages to walk you through the changes you need to make to the template.

You can create a new module using `nf-core modules create`.

This command can be used both when writing a module for the shared [nf-core/modules](https://github.com/nf-core/modules) repository,
and also when creating local modules for a pipeline.

Which type of repository you are working in is detected by the `repository_type` flag in a `.nf-core.yml` file in the root directory,
set to either `pipeline` or `modules`.
The command will automatically look through parent directories for this file to set the root path, so that you can run the command in a subdirectory.
It will start in the current working directory, or whatever is specified with `--dir <directory>`.

The `nf-core modules create` command will prompt you with the relevant questions in order to create all of the necessary module files.

<!-- RICH-CODEX
working_dir: tmp
timeout: 10
before_command: git clone https://github.com/nf-core/modules.git && cd modules
fake_command: nf-core modules create fastqc --author @nf-core-bot  --label process_low --meta --force
-->

![`cd modules && nf-core modules create fastqc --author @nf-core-bot  --label process_low --meta --force`](../images/nf-core-modules-create.svg)
