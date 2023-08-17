---
title: Update subworkflows
description: Update subworkflows installed in a pipeline.
weight: 50
section: subworkflows
---

You can update subworkflows installed from a remote repository in your pipeline using `nf-core subworkflows update`.

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
before_command: >
  echo "repository_type: pipeline" >> .nf-core.yml
-->

![`nf-core subworkflows update --all --no-preview`](../images/nf-core-subworkflows-update.svg)

You can pass the subworkflow name as an optional argument to `nf-core subworkflows update` like above or select it from the list of available subworkflows by only running `nf-core subworkflows update`.

There are six additional flags that you can use with this command:

- `--dir`: Pipeline directory, the default is the current working directory.
- `--force`: Reinstall subworkflow even if it appears to be up to date
- `--prompt`: Select the subworkflow version using a cli prompt.
- `--sha <commit_sha>`: Install the subworkflow at a specific commit from the `nf-core/modules` repository.
- `--preview/--no-preview`: Show the diff between the installed files and the new version before installing.
- `--save-diff <filename>`: Save diffs to a file instead of updating in place. The diffs can then be applied with `git apply <filename>`.
- `--all`: Use this flag to run the command on all subworkflows in the pipeline.
- `--update-deps`: Use this flag to automatically update all dependencies of a subworkflow.

If you don't want to update certain subworkflows or want to update them to specific versions, you can make use of the `.nf-core.yml` configuration file. For example, you can prevent the `bam_rseqc` subworkflow installed from `nf-core/modules` from being updated by adding the following to the `.nf-core.yml` file:

```yaml
update:
  https://github.com/nf-core/modules.git:
    nf-core:
      bam_rseqc: False
```

If you want this subworkflow to be updated only to a specific version (or downgraded), you could instead specifiy the version:

```yaml
update:
  https://github.com/nf-core/modules.git:
    nf-core:
      bam_rseqc: "36a77f7c6decf2d1fb9f639ae982bc148d6828aa"
```

This also works at the repository level. For example, if you want to exclude all modules and subworkflows installed from `nf-core/modules` from being updated you could add:

```yaml
update:
  https://github.com/nf-core/modules.git:
    nf-core: False
```

or if you want all subworkflows in `nf-core/modules` at a specific version:

```yaml
update:
  https://github.com/nf-core/modules.git:
    nf-core: "e937c7950af70930d1f34bb961403d9d2aa81c7"
```

Note that the subworkflow versions specified in the `.nf-core.yml` file has higher precedence than versions specified with the command line flags, thus aiding you in writing reproducible pipelines.
