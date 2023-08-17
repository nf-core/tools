---
title: Test a subworkflow
description: Run the tests for a subworkflow using pytest.
weight: 100
section: subworkflows
---

To run unit tests of a subworkflow that you have installed or the test created by the command [`nf-core subworkflow create-test-yml`](#create-a-subworkflow-test-config-file), you can use `nf-core subworkflows test` command. This command runs the tests specified in `tests/subworkflows/<subworkflow_name>/test.yml` file using [pytest](https://pytest-workflow.readthedocs.io/en/stable/).

:::info
This command uses the pytest argument `--git-aware` to avoid copying the whole `.git` directory and files ignored by `git`. This means that it will only include files listed by `git ls-files`. Remember to **commit your changes** after adding a new subworkflow to add the new files to your git index.
:::

You can specify the subworkflow name in the form TOOL/SUBTOOL in command line or provide it later by prompts.

<!-- RICH-CODEX
working_dir: tmp/modules
timeout: 30
extra_env:
  PROFILE: 'conda'
-->

![`nf-core subworkflows test bam_rseqc --no-prompts`](../images/nf-core-subworkflows-test.svg)
