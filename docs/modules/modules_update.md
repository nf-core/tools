---
title: Update modules
description: Update modules installed from a remote repository in a pipeline.
weight: 50
section: modules
---

You can update modules installed from a remote repository in your pipeline using `nf-core modules update`.

<!-- RICH-CODEX
working_dir: tmp/nf-core-nextbigthing
-->

![`nf-core modules update --all --no-preview`](../images/nf-core-modules-update.svg)

You can pass the module name as an optional argument to `nf-core modules update` instead of using the cli prompt, eg: `nf-core modules update fastqc`. You can specify a pipeline directory other than the current working directory by using the `--dir <pipeline dir>`.

There are five additional flags that you can use with this command:

- `--force`: Reinstall module even if it appears to be up to date
- `--prompt`: Select the module version using a cli prompt.
- `--sha <commit_sha>`: Install the module at a specific commit from the `nf-core/modules` repository.
- `--preview/--no-preview`: Show the diff between the installed files and the new version before installing.
- `--save-diff <filename>`: Save diffs to a file instead of updating in place. The diffs can then be applied with `git apply <filename>`.
- `--all`: Use this flag to run the command on all modules in the pipeline.

If you don't want to update certain modules or want to update them to specific versions, you can make use of the `.nf-core.yml` configuration file. For example, you can prevent the `star/align` module installed from `nf-core/modules` from being updated by adding the following to the `.nf-core.yml` file:

```yaml
update:
  https://github.com/nf-core/modules.git:
    nf-core:
      star/align: False
```

If you want this module to be updated only to a specific version (or downgraded), you could instead specifiy the version:

```yaml
update:
  https://github.com/nf-core/modules.git:
    nf-core:
      star/align: "e937c7950af70930d1f34bb961403d9d2aa81c7"
```

This also works at the repository level. For example, if you want to exclude all modules installed from `nf-core/modules` from being updated you could add:

```yaml
update:
  https://github.com/nf-core/modules.git:
    nf-core: False
```

or if you want all modules in `nf-core/modules` at a specific version:

```yaml
update:
  https://github.com/nf-core/modules.git:
    nf-core: "e937c7950af70930d1f34bb961403d9d2aa81c7"
```

Note that the module versions specified in the `.nf-core.yml` file has higher precedence than versions specified with the command line flags, thus aiding you in writing reproducible pipelines.
