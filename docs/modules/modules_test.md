---
title: Linting modules
description: Check a module against nf-core guidelines.
weight: 100
section: modules
---

# Run the tests for a module using pytest

To run unit tests of a module that you have installed or the test created by the command [`nf-core modules create-test-yml`](#create-a-module-test-config-file), you can use `nf-core modules test` command. This command runs the tests specified in `modules/tests/software/<tool>/<subtool>/test.yml` file using [pytest](https://pytest-workflow.readthedocs.io/en/stable/).

:::info
This command uses the pytest argument `--git-aware` to avoid copying the whole `.git` directory and files ignored by `git`. This means that it will only include files listed by `git ls-files`. Remember to **commit your changes** after adding a new module to add the new files to your git index.
:::

You can specify the module name in the form TOOL/SUBTOOL in command line or provide it later by prompts.

<!-- RICH-CODEX
working_dir: tmp/modules
timeout: 30
extra_env:
  PROFILE: 'conda'
-->

![`nf-core modules test samtools/view --no-prompts`](../images/nf-core-modules-test.svg)
