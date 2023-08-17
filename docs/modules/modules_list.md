---
title: List modules
description: List modules installed in a pipeline or available in a remote repository.
weight: 20
section: modules
---

# Introduction

The `nf-core modules list` command provides the subcommands `remote` and `local` for listing modules installed in a remote repository and in the local pipeline respectively. Both subcommands allow to use a pattern for filtering the modules by keywords eg: `nf-core modules list <subcommand> <keyword>`.

## List remote modules

To list all modules available on [nf-core/modules](https://github.com/nf-core/modules), you can use
`nf-core modules list remote`, which will print all available modules to the terminal.

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
head: 25
-->

![`nf-core modules list remote`](../images/nf-core-modules-list-remote.svg)

## List installed modules

To list modules installed in a local pipeline directory you can use `nf-core modules list local`. This will list the modules install in the current working directory by default. If you want to specify another directory, use the `--dir <pipeline_dir>` flag.

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
head: 25
-->

![`nf-core modules list local`](../images/nf-core-modules-list-local.svg)
