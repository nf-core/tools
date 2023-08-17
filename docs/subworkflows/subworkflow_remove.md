---
title: Remove a subworkflow
description: Remove a subworkflow from a pipeline.
weight: 60
section: subworkflows
---

To delete a subworkflow from your pipeline, run `nf-core subworkflows remove`.

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
before_command: >
  echo "repository_type: pipeline" >> .nf-core.yml
-->

![`nf-core subworkflows remove bam_rseqc`](../images/nf-core-subworkflows-remove.svg)

You can pass the subworkflow name as an optional argument to `nf-core subworkflows remove` like above or select it from the list of available subworkflows by only running `nf-core subworkflows remove`. To specify the pipeline directory, use `--dir <pipeline_dir>`.
