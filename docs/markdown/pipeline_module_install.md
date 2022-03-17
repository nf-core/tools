---
title: Modules 
subtitle: Install modules in a pipeline
---

# Install modules in a pipeline

You can install modules from [nf-core/modules](https://github.com/nf-core/modules) in your pipeline using `nf-core modules install`.
A module installed this way will be installed to the `./modules/nf-core/modules` directory.

```console
$ nf-core modules install
                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2

? Tool name: cat/fastq
INFO     Installing cat/fastq
INFO     Downloaded 3 files to ./modules/nf-core/modules/cat/fastq
```

You can pass the module name as an optional argument to `nf-core modules install` instead of using the cli prompt, eg: `nf-core modules install fastqc`. You can specify a pipeline directory other than the current working directory by using the `--dir <pipeline dir>`.

There are three additional flags that you can use when installing a module:

* `--force`: Overwrite a previously installed version of the module.
* `--prompt`: Select the module version using a cli prompt.
* `--sha <commit_sha>`: Install the module at a specific commit from the `nf-core/modules` repository.
