---
title: Modules
subtitle: Update modules in a pipeline
---

# Update modules in a pipeline

You can update modules installed from a remote repository in your pipeline using `nf-core modules update`.

```console
$ nf-core modules update
                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2

? Tool name: fastqc
INFO     Updating 'nf-core/modules/fastqc'
INFO     Downloaded 3 files to ./modules/nf-core/modules/fastqc
```

You can pass the module name as an optional argument to `nf-core modules update` instead of using the cli prompt, eg: `nf-core modules update fastqc`. You can specify a pipeline directory other than the current working directory by using the `--dir <pipeline dir>`.

There are five additional flags that you can use with this command:

- `--force`: Reinstall module even if it appears to be up to date
- `--prompt`: Select the module version using a cli prompt.
- `--sha <commit_sha>`: Install the module at a specific commit from the `nf-core/modules` repository.
- `--diff`: Show the diff between the installed files and the new version before installing.
- `--diff-file <filename>`: Specify where the diffs between the local and remote versions of a module should be written
- `--all`: Use this flag to run the command on all modules in the pipeline.

If you don't want to update certain modules or want to update them to specific versions, you can make use of the `.nf-core.yml` configuration file. For example, you can prevent the `star/align` module installed from `nf-core/modules` from being updated by adding the following to the `.nf-core.yml` file:

```yaml
update:
  nf-core/modules:
    star/align: False
```

If you want this module to be updated only to a specific version (or downgraded), you could instead specifiy the version:

```yaml
update:
  nf-core/modules:
    star/align: "e937c7950af70930d1f34bb961403d9d2aa81c7"
```

This also works at the repository level. For example, if you want to exclude all modules installed from `nf-core/modules` from being updated you could add:

```yaml
update:
  nf-core/modules: False
```

or if you want all modules in `nf-core/modules` at a specific version:

```yaml
update:
  nf-core/modules: "e937c7950af70930d1f34bb961403d9d2aa81c7"
```

Note that the module versions specified in the `.nf-core.yml` file has higher precedence than versions specified with the command line flags, thus aiding you in writing reproducible pipelines.
