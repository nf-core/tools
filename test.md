### Check a module against nf-core guidelines

Run the `nf-core modules lint` command to check modules in the current working directory (pipeline or nf-core/modules clone) against nf-core guidelines.

Use the `--all` flag to run linting on all modules found. Use `--dir <pipeline_dir>` to specify another directory than the current working directory.
<!-- RICH-CODEX
working_dir: tmp/modules
before_command: sed 's/1.13a/1.10/g' modules/multiqc/main.nf > modules/multiqc/main.nf.tmp && mv modules/multiqc/main.nf.tmp modules/multiqc/main.nf
-->
![`nf-core modules lint multiqc`](docs/images/nf-core-modules-lint.svg)

### Run the tests for a module using pytest

To run unit tests of a module that you have installed or the test created by the command [`nf-core mdoules create-test-yml`](#create-a-module-test-config-file), you can use `nf-core modules test` command. This command runs the tests specified in `modules/tests/software/<tool>/<subtool>/test.yml` file using [pytest](https://pytest-workflow.readthedocs.io/en/stable/).

You can specify the module name in the form TOOL/SUBTOOL in command line or provide it later by prompts.
<!-- RICH-CODEX
working_dir: tmp/modules
timeout: 30
extra_env:
  PROFILE: 'conda'
-->
![`nf-core modules test samtools/view --no-prompts`](docs/images/nf-core-modules-test.svg)

### Bump bioconda and container versions of modules in

If you are contributing to the `nf-core/modules` repository and want to bump bioconda and container versions of certain modules, you can use the `nf-core modules bump-versions` helper tool. This will bump the bioconda version of a single or all modules to the latest version and also fetch the correct Docker and Singularity container tags.
<!-- RICH-CODEX
working_dir: tmp/modules
-->
![`nf-core modules bump-versions multiqc`](docs/images/nf-core-modules-bump-version.svg)

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

### Generate the name for a multi-tool container image

When you want to use an image of a multi-tool container and you know the specific dependencies and their versions of that container, for example, by looking them up in the [BioContainers hash.tsv](https://github.com/BioContainers/multi-package-containers/blob/master/combinations/hash.tsv), you can use the `nf-core modules mulled` helper tool. This tool generates the name of a BioContainers mulled image.

<!-- RICH-CODEX
working_dir: tmp/modules
-->
![`nf-core modules mulled pysam==0.16.0.1 biopython==1.78`](docs/images/nf-core-modules-mulled.svg)
```console
$ nf-core modules mulled pysam==0.16.0.1 biopython==1.78

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.4


mulled-v2-3a59640f3fe1ed11819984087d31d68600200c3f:185a25ca79923df85b58f42deb48f5ac4481e91f-0
```
