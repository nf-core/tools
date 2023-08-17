---
title: Sync a pipeline
description: Manually synchronise a pipeline with the nf-core template.
weight: 90
section: pipelines
---

# Introduction

Over time, the main nf-core pipeline template is updated. To keep all nf-core pipelines up to date,
we synchronise these updates automatically when new versions of nf-core/tools are released.
This is done by maintaining a special `TEMPLATE` branch, containing a vanilla copy of the nf-core template
with only the variables used when it first ran (name, description etc.). This branch is updated and a
pull-request can be made with just the updates from the main template code.

Note that pipeline synchronisation happens automatically each time nf-core/tools is released, creating an automated pull-request on each pipeline.
**As such, you do not normally need to run this command yourself!**

This command takes a pipeline directory and attempts to run this synchronisation.
Usage is `nf-core sync`, eg:

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
before_command: git config --global user.email "nf-core_bot@example.com" && git config --global user.name "nf-core_bot" &&  git commit -am "Bump version"
-->

![`nf-core sync`](../images/nf-core-sync.svg)

The sync command tries to check out the `TEMPLATE` branch from the `origin` remote or an existing local branch called `TEMPLATE`.
It will fail if it cannot do either of these things.
The `nf-core create` command should make this template automatically when you first start your pipeline.
Please see the [nf-core website sync documentation](https://nf-co.re/developers/sync) if you have difficulties.

To specify a directory to sync other than the current working directory, use the `--dir <pipline_dir>`.

By default, the tool will collect workflow variables from the current branch in your pipeline directory.
You can supply the `--from-branch` flag to specific a different branch.

Finally, if you give the `--pull-request` flag, the command will push any changes to the remote and attempt to create a pull request using the GitHub API.
The GitHub username and repository name will be fetched from the remote url (see `git remote -v | grep origin`), or can be supplied with `--username` and `--github-repository`.

To create the pull request, a personal access token is required for API authentication.
These can be created at [https://github.com/settings/tokens](https://github.com/settings/tokens).
Supply this using the `--auth-token` flag.
