---
title: Bump a pipeline version number
description: Bump the version number of a nf-core pipeline.
weight: 90
section: pipelines
---

# Introduction

When releasing a new version of a nf-core pipeline, version numbers have to be updated in several different places. The helper command `nf-core bump-version` automates this for you to avoid manual errors (and frustration!).

The command uses results from the linting process, so will only work with workflows that pass these tests.

Usage is `nf-core bump-version <new_version>`, eg:

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
-->

![`nf-core bump-version 1.1`](../images/nf-core-bump-version.svg)

You can change the directory from the current working directory by specifying `--dir <pipeline_dir>`. To change the required version of Nextflow instead of the pipeline version number, use the flag `--nextflow`.
