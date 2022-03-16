## Modules

With the advent of [Nextflow DSL2](https://www.nextflow.io/docs/latest/dsl2.html), we are creating a centralised repository of modules.
These are software tool process definitions that can be imported into any pipeline.
This allows multiple pipelines to use the same code for share tools and gives a greater degree of granulairy and unit testing.

The nf-core DSL2 modules repository is at <https://github.com/nf-core/modules>

### Custom remote modules

The modules supercommand comes with two flags for specifying a custom remote:

* `--github-repository <github repo>`: Specify the repository from which the modules should be fetched. Defaults to `nf-core/modules`.
* `--branch <branch name>`: Specify the branch from which the modules shoudl be fetched. Defaults to `master`.

Note that a custom remote must follow a similar directory structure to that of `nf-core/moduleś` for the `nf-core modules` commands to work properly.

### Private remote modules

In order to get access to your private modules repo, you need to create
the `~/.config/gh/hosts.yml` file, which is the same file required by
[GitHub CLI](https://cli.github.com/) to deal with private repositories.
Such file is structured as follow:

```conf
github.com:
    oauth_token: <your github access token>
    user: <your github user>
    git_protocol: <ssh or https are valid choices>
```

The easiest way to create this configuration file is through _GitHub CLI_: follow
its [installation instructions](https://cli.github.com/manual/installation)
and then call:

```bash
gh auth login
```

After that, you will be able to list and install your private modules without
providing your github credentials through command line, by using `--github-repository`
and `--branch` options properly.
See the documentation on [gh auth login](https://cli.github.com/manual/gh_auth_login>)
to get more information.

### List modules

The `nf-core modules list` command provides the subcommands `remote` and `local` for listing modules installed in a remote repository and in the local pipeline respectively. Both subcommands come with the `--key <keywords>` option for filtering the modules by keywords.

#### List remote modules

To list all modules available on [nf-core/modules](https://github.com/nf-core/modules), you can use
`nf-core modules list remote`, which will print all available modules to the terminal.

```console
$ nf-core modules list remote
                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2


INFO     Modules available from nf-core/modules (master)

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Module Name                    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ bandage/image                  │
│ bcftools/consensus             │
│ bcftools/filter                │
│ bcftools/isec                  │
│ bcftools/merge                 │
│ bcftools/mpileup               │
│ bcftools/stats                 │
│ ..truncated..                  │
└────────────────────────────────┘
```

#### List installed modules

To list modules installed in a local pipeline directory you can use `nf-core modules list local`. This will list the modules install in the current working directory by default. If you want to specify another directory, use the `--dir <pipeline_dir>` flag.

```console
$ nf-core modules list local
                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2


INFO     Modules installed in '.':

┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Module Name ┃ Repository      ┃ Version SHA ┃ Message                                                ┃ Date       ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ fastqc      │ nf-core/modules │ e937c79...  │ Rename software/ directory to modules/ ...truncated... │ 2021-07-07 │
│ multiqc     │ nf-core/modules │ e937c79...  │ Rename software/ directory to modules/ ...truncated... │ 2021-07-07 │
└─────────────┴─────────────────┴─────────────┴────────────────────────────────────────────────────────┴────────────┘
```

## Show information about a module

For quick help about how a module works, use `nf-core modules info <tool>`.
This shows documentation about the module on the command line, similar to what's available on the
[nf-core website](https://nf-co.re/modules).

```console
$ nf-core modules info fastqc

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.3.dev0 - https://nf-co.re


╭─ Module: fastqc  ───────────────────────────────────────────────────────────────────────────────────────╮
│ 🌐 Repository: nf-core/modules                                                                          │
│ 🔧 Tools: fastqc                                                                                        │
│ 📖 Description: Run FastQC on sequenced reads                                                           │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────╯
               ╷                                                                                  ╷
 📥 Inputs     │Description                                                                       │Pattern
╺━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━╸
  meta  (map)  │Groovy Map containing sample information e.g. [ id:'test', single_end:false ]     │
╶──────────────┼──────────────────────────────────────────────────────────────────────────────────┼───────╴
  reads  (file)│List of input FastQ files of size 1 and 2 for single-end and paired-end data,     │
               │respectively.                                                                     │
               ╵                                                                                  ╵
                  ╷                                                                       ╷
 📤 Outputs       │Description                                                            │        Pattern
╺━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━╸
  meta  (map)     │Groovy Map containing sample information e.g. [ id:'test',             │
                  │single_end:false ]                                                     │
╶─────────────────┼───────────────────────────────────────────────────────────────────────┼───────────────╴
  html  (file)    │FastQC report                                                          │*_{fastqc.html}
╶─────────────────┼───────────────────────────────────────────────────────────────────────┼───────────────╴
  zip  (file)     │FastQC report archive                                                  │ *_{fastqc.zip}
╶─────────────────┼───────────────────────────────────────────────────────────────────────┼───────────────╴
  versions  (file)│File containing software versions                                      │   versions.yml
                  ╵                                                                       ╵

 💻  Installation command: nf-core modules install fastqc

```

### Install modules in a pipeline

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

### Update modules in a pipeline

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

* `--force`: Reinstall module even if it appears to be up to date
* `--prompt`: Select the module version using a cli prompt.
* `--sha <commit_sha>`: Install the module at a specific commit from the `nf-core/modules` repository.
* `--diff`: Show the diff between the installed files and the new version before installing.
* `--diff-file <filename>`: Specify where the diffs between the local and remote versions of a module should be written
* `--all`: Use this flag to run the command on all modules in the pipeline.

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

### Remove a module from a pipeline

To delete a module from your pipeline, run `nf-core modules remove`.

```console
$ nf-core modules remove

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2

? Tool name: star/align
INFO     Removing star/align
```

You can pass the module name as an optional argument to `nf-core modules remove` instead of using the cli prompt, eg: `nf-core modules remove fastqc`. To specify the pipeline directory, use `--dir <pipeline_dir>`.

### Create a new module

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

### Create a module test config file

All modules on [nf-core/modules](https://github.com/nf-core/modules) have a strict requirement of being unit tested using minimal test data.
To help developers build new modules, the `nf-core modules create-test-yml` command automates the creation of the yaml file required to document the output file `md5sum` and other information generated by the testing.
After you have written a minimal Nextflow script to test your module `modules/tests/software/<tool>/<subtool>/main.nf`, this command will run the tests for you and create the `modules/tests/software/<tool>/<subtool>/test.yml` file.

```console
$ nf-core modules create-test-yml

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2


INFO     Press enter to use default values (shown in brackets) or type your own responses
? Tool name: star/align
Test YAML output path (- for stdout) (tests/software/star/align/test.yml):
File exists! 'tests/software/star/align/test.yml' Overwrite? [y/n]: y
INFO     Looking for test workflow entry points: 'tests/software/star/align/main.nf'
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
INFO     Building test meta for entry point 'test_star_alignment_single_end'
Test name (star align test_star_alignment_single_end):
Test command (nextflow run tests/software/star/align -entry test_star_alignment_single_end -c tests/config/nextflow.config):
Test tags (comma separated) (star_alignment_single_end,star_align,star):
Test output folder with results (leave blank to run test):
? Choose software profile  Docker
INFO     Running 'star/align' test with command:
         nextflow run tests/software/star/align -entry test_star_alignment_single_end -c tests/config/nextflow.config --outdir
         /var/folders/bq/451scswn2dn4npxhf_28lyt40000gn/T/tmp_p22f8bg
INFO     Test workflow finished!
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
INFO     Building test meta for entry point 'test_star_alignment_paired_end'
Test name (star align test_star_alignment_paired_end):
Test command (nextflow run tests/software/star/align -entry test_star_alignment_paired_end -c tests/config/nextflow.config):
Test tags (comma separated) (star_align,star_alignment_paired_end,star):
Test output folder with results (leave blank to run test):
INFO     Running 'star/align' test with command:
         nextflow run tests/software/star/align -entry test_star_alignment_paired_end -c tests/config/nextflow.config --outdir
         /var/folders/bq/451scswn2dn4npxhf_28lyt40000gn/T/tmp5qc3kfie
INFO     Test workflow finished!
INFO     Writing to 'tests/software/star/align/test.yml'
```

### Check a module against nf-core guidelines

Run the `nf-core modules lint` command to check modules in the current working directory (pipeline or nf-core/modules clone) against nf-core guidelines.

Use the `--all` flag to run linting on all modules found. Use `--dir <pipeline_dir>` to specify another directory than the current working directory.

```console
$ nf-core modules lint
                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2

? Lint all modules or a single named module? Named module
? Tool name: star/align
INFO     Linting pipeline: .
INFO     Linting module: star/align
╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Module lint results                                                                                                │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ [!] 1 Test Warning                                                                                                 │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭───────────────────┬────────────────────────────────────────────┬───────────────────────────────────────────────────╮
│ Module name       │ File path                                  │ Test message                                      │
├───────────────────┼────────────────────────────────────────────┼───────────────────────────────────────────────────┤
│ star/align        │ modules/nf-core/modules/star/align/main.nf │ Conda update: bioconda::star 2.6.1d -> 2.7.9a     │
╰───────────────────┴────────────────────────────────────────────┴───────────────────────────────────────────────────╯
╭──────────────────────╮
│ LINT RESULTS SUMMARY │
├──────────────────────┤
│ [✔]  21 Tests Passed │
│ [!]   1 Test Warning │
│ [✗]   0 Test Failed  │
╰──────────────────────╯
```

### Bump bioconda and container versions of modules in

If you are contributing to the `nf-core/modules` repository and want to bump bioconda and container versions of certain modules, you can use the `nf-core modules bump-versions` helper tool. This will bump the bioconda version of a single or all modules to the latest version and also fetch the correct Docker and Singularity container tags.

```console
$ nf-core modules bump-versions -d modules

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2



? Bump versions for all modules or a single named module?  Named module
? Tool name: bcftools/consensus
╭───────────────────────────╮
│ [!] 1  Module updated     │
╰───────────────────────────╯
╭─────────────────────────────────────────────────────────────╮
│ Module name               │ Update message                  │
├───────────────────────────┤─────────────────────────────────┤
│ bcftools/consensus        │ Module updated:  1.11 --> 1.12  │
╰─────────────────────────────────────────────────────────────╯
```

If you don't want to update certain modules or want to update them to specific versions, you can make use of the `.nf-core.yml` configuration file. For example, you can prevent the `star/align` module from being updated by adding the following to the `.nf-core.yml` file:

```yaml
bump-versions:
  star/align: False
```

If you want this module to be updated only to a specific version (or downgraded), you could instead specifiy the version:

```yaml
bump-versions:
  star/align: "2.6.1d"
```