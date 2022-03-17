---
title: Modules
subtitle: Create a new module
---

# Create a new module

This command creates a new nf-core module from the nf-core module template.
This ensures that your module follows the nf-core guidelines.
The template contains extensive `TODO` messages to walk you through the changes you need to make to the template.

You can create a new module using `nf-core modules create`.

This command can be used both when writing a module for the shared [nf-core/modules](https://github.com/nf-core/modules) repository,
and also when creating local modules for a pipeline.

Which type of repository you are working in is detected by the `repository_type` flag in a `.nf-core.yml` file in the root directory,
set to either `pipeline` or `modules`.
The command will automatically look through parent directories for this file to set the root path, so that you can run the command in a subdirectory.
It will start in the current working directory, or whatever is specified with `--dir <directory>`.

The `nf-core modules create` command will prompt you with the relevant questions in order to create all of the necessary module files.

```console
$ nf-core modules create

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2


INFO     Press enter to use default values (shown in brackets) or type your own responses. ctrl+click underlined text to open links.
Name of tool/subtool: star/align
INFO     Using Bioconda package: 'bioconda::star=2.6.1d'
INFO     Using Docker / Singularity container with tag: 'star:2.6.1d--0'
GitHub Username: (@ewels):
INFO     Provide an appropriate resource label for the process, taken from the nf-core pipeline template.
         For example: process_low, process_medium, process_high, process_long
? Process resource label: process_high
INFO     Where applicable all sample-specific information e.g. 'id', 'single_end', 'read_group' MUST be provided as an input via a
         Groovy Map called 'meta'. This information may not be required in some instances, for example indexing reference genome files.
Will the module require a meta map of sample information? [y/n] (y): y
INFO     Created / edited following files:
           ./software/star/align/main.nf
           ./software/star/align/meta.yml
           ./tests/software/star/align/main.nf
           ./tests/software/star/align/test.yml
           ./tests/config/pytest_modules.yml
```
