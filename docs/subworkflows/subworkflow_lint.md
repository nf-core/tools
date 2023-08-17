---
title: Lint a subworkflows
description: Check a subworkflow against nf-core guidelines.
weight: 90
section: subworkflows
---

Run the `nf-core subworkflows lint` command to check subworkflows in the current working directory (a pipeline or a clone of nf-core/modules) against nf-core guidelines.

Use the `--all` flag to run linting on all subworkflows found. Use `--dir <pipeline_dir>` to specify a different directory than the current working directory.

<!-- RICH-CODEX
working_dir: tmp/modules
extra_env:
  PROFILE: 'conda'
-->

![`nf-core subworkflows lint bam_stats_samtools`](../images/nf-core-subworkflows-lint.svg)
