---
title: Remove a module
description: Uninstall a module from a pipeline.
weight: 60
section: modules
---

To delete a module from your pipeline, run `nf-core modules remove`.

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
-->

![`nf-core modules remove abacas`](../images/nf-core-modules-remove.svg)

You can pass the module name as an optional argument to `nf-core modules remove` instead of using the cli prompt, eg: `nf-core modules remove fastqc`. To specify the pipeline directory, use `--dir <pipeline_dir>`.
