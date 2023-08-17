---
title: List subworkflows
description: List subworkflows installed in a pipeline or available in a remote repository.
weight: 20
section: subworkflows
---

The `nf-core subworkflows list` command provides the subcommands `remote` and `local` for listing subworkflows installed in a remote repository and in the local pipeline respectively. Both subcommands allow to use a pattern for filtering the subworkflows by keywords eg: `nf-core subworkflows list <subworkflow_name> <keyword>`.

#### List remote subworkflows

To list all subworkflows available on [nf-core/modules](https://github.com/nf-core/modules), you can use
`nf-core subworkflows list remote`, which will print all available subworkflows to the terminal.

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
head: 25
-->

![`nf-core subworkflows list remote`](../images/nf-core-subworkflows-list-remote.svg)

#### List installed subworkflows

To list subworkflows installed in a local pipeline directory you can use `nf-core subworkflows list local`. This will list the subworkflows install in the current working directory by default. If you want to specify another directory, use the `--dir <pipeline_dir>` flag.

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
before_command: >
  echo "repository_type: pipeline" >> .nf-core.yml
head: 25
-->

![`nf-core subworkflows list local`](../images/nf-core-subworkflows-list-local.svg)
