---
title: Install modules
description: Install modules from a remote repository in a pipeline.
weight: 50
section: modules
---

You can install modules from [nf-core/modules](https://nf-co.re/modules) in your pipeline using `nf-core modules install`.
A module installed this way will be installed to the `./modules/nf-core/` directory.

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
-->

![`nf-core modules install abacas`](../images/nf-core-modules-install.svg)

You can pass the module name as an optional argument to `nf-core modules install` instead of using the cli prompt, eg: `nf-core modules install fastqc`. You can specify a pipeline directory other than the current working directory by using the `--dir <pipeline dir>`.

There are three additional flags that you can use when installing a module:

- `--force`: Overwrite a previously installed version of the module.
- `--prompt`: Select the module version using a cli prompt.
- `--sha <commit_sha>`: Install the module at a specific commit.
