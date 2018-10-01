# nf-core/tools: Changelog

## [v1.2](https://github.com/nf-core/tools/releases/tag/1.2) - 2018-10-01
* Updated the `nf-core release` command
    * Now called `nf-core bump-versions` instead
    * New flag `--nextflow` to change the required nextflow version instead
* Template updates
    * Simpler installation of the `nf-core` helper tool, now directly from PyPI
    * Bump minimum nextflow version to `0.31.1` (required for built in `manifest.nextflowVersion` check)
    * New `withName` syntax for configs
    * Travis tests fail if PRs come against the `master` branch, slightly refactored
    * Improved GitHub contributing instructions and pull request / issue templates
* New lint tests
    * `.travis.yml` test for PRs made against the `master` branch
    * Automatic `--release` option not used if the travis repo is `nf-core/tools`
    * Warnings if depreciated variables `params.version` and `params.nf_required_version` are found
* New `nf-core licences` subcommand to show licence for each conda package in a workflow
* `nf-core list` now has options for sorting pipeline nicely
* Latest version of conda used in nf-core base docker image
* Updated PyPI deployment to  correctly parse the markdown readme (hopefully!)
* New GitHub contributing instructions and pull request template

## [v1.1](https://github.com/nf-core/tools/releases/tag/1.1) - 2018-08-14
Very large release containing lots of work from the first nf-core hackathon, held in SciLifeLab Stockholm.

* The [Cookiecutter template](https://github.com/nf-core/cookiecutter) has been merged into tools
    * The old repo above has been archived
    * New pipelines are now created using the command `nf-core create`
    * The nf-core template and associated linting are now controlled under the same version system
* Large number of template updates and associated linting changes
    * New simplified cookicutter variable usage
    * Refactored documentation - simplified and reduced duplication
    * Better `manifest` variables instead of `params` for pipeline name and version
    * New integrated nextflow version checking
    * Updated travis docker pull command to use tagging to allow release tests to pass
    * Reverted Docker and Singularity syntax to use `ENV` hack again
* Improved Python readme parsing for PyPI
* Updated Travis tests to check that the correct `dev` branch is being targeted
* New sync tool to automate pipeline updates
    * Once initial merges are complete, a nf-core bot account will create PRs for future template updates

## [v1.0.1](https://github.com/nf-core/tools/releases/tag/1.0.1) - 2018-07-18

The version 1.0 of nf-core tools cannot be installed from PyPi. This patch fixes it, by getting rid of the requirements.txt plus declaring the dependent modules in the setup.py directly.

## [v1.0](https://github.com/nf-core/tools/releases/tag/1.0) - 2018-06-12

Initial release of the nf-core helper tools package. Currently includes four subcommands:

* `nf-core list`: List nf-core pipelines with local info
* `nf-core download`: Download a pipeline and singularity container
* `nf-core lint`: Check pipeline against nf-core guidelines
* `nf-core release`: Update nf-core pipeline version number
