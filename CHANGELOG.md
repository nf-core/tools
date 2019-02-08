# nf-core/tools: Changelog

## v1.5dev

#### Template pipeline
* Summary now logs details of the cluster profile used if from [nf-core/configs](https://github.com/nf-core/configs)
* Dockerhub is used in favor of Singularity Hub for pulling when using the Singularity profile
* Changed default container tag from latest to dev
* Brought the logo to life
* Change the default filenames for the pipeline trace files

#### Tools helper code
* New `nf-core launch` command to interactively launch nf-core pipelines from command-line
* Drop Python 3.4 support
* `nf-core list` now only shows a value for _"is local latest version"_ column if there is a local copy.
* `nf-core lint` now properly searches for conda packages in default channels
* Linting correctly validates version pinning for packages from PyPI
* Lint markdown formatting in automated tests
  * Added `markdownlint-cli` for checking Markdown syntax
* Syncing now reads from a `blacklist.json` in order to exclude pipelines from being synced if necessary.
* Added nf-core tools API description to assist developers with the classes and functions available.
  * Docs are automatically built by Travis CI and updated on the nf-co.re website.
* Introduced test for filtering remote workflows by keyword.
* Build tools python API docs
  * Use Travis job for api doc generation and publish
* Bump `conda` to 4.5.12 in base nf-core Dockerfile
* `nf-core bump-version` now stops before making changes if the linting fails
* Code test coverage
  * Introduced test for filtering remote workflows by keyword


## [v1.4](https://github.com/nf-core/tools/releases/tag/1.4) - 2018-12-12 Tantalum Butterfly

#### Template pipeline
* Institutional custom config profiles moved to github `nf-core/configs`
  * These will now be maintained centrally as opposed to being shipped with the pipelines in `conf/`
  * Load `base.config` by default for all profiles
  * Removed profiles named `standard` and `none`
  * Added parameter `--igenomesIgnore` so `igenomes.config` is not loaded if parameter clashes are observed
  * Added parameter `--custom_config_version` for custom config version control. Can use this parameter to provide commit id for reproducibility. Defaults to `master`
  * Deleted custom configs from template in `conf/` directory i.e. `uzh.config`, `binac.config` and `cfc.config`
* `multiqc_config` and `output_md` are now put into channels instead of using the files directly (see issue [#222](https://github.com/nf-core/tools/issues/222))
* Added `local.md` to cookiecutter template in `docs/configuration/`. This was referenced in `README.md` but not present.
* Major overhaul of docs to add/remove parameters, unify linking of files and added description for providing custom configs where necessary
* Travis: Pull the `dev` tagged docker image for testing
* Removed UPPMAX-specific documentation from the template.

#### Tools helper code
* Make Travis CI tests fail on pull requests if the `CHANGELOG.md` file hasn't been updated
* Minor bugfixing in Python code (eg. removing unused import statements)
* Made the web requests caching work on multi-user installations
* Handle exception if nextflow isn't installed
* Linting: Update for Travis: Pull the `dev` tagged docker image for testing

## [v1.3](https://github.com/nf-core/tools/releases/tag/1.3) - 2018-11-21
* `nf-core create` command line interface updated
  * Interactive prompts for required arguments if not given
  * New flag for workflow author
* Updated channel order for bioconda/conda-forge channels in environment.yaml
* Increased code coverage for sub command `create` and `licenses`
* Fixed nasty dependency hell issue between `pytest` and `py` package in Python 3.4.x
* Introduced `.coveragerc` for pytest-cov configuration, which excludes the pipeline template now from being reported
* Fix [189](https://github.com/nf-core/tools/issues/189): Check for given conda and PyPi package dependencies, if their versions exist
* Added profiles for `cfc`,`binac`, `uzh` that can be synced across pipelines
  * Ordering alphabetically for profiles now
* Added `pip install --upgrade pip` to `.travis.yml` to update pip in the Travis CI environment

## [v1.2](https://github.com/nf-core/tools/releases/tag/1.2) - 2018-10-01
* Updated the `nf-core release` command
  * Now called `nf-core bump-versions` instead
  * New flag `--nextflow` to change the required nextflow version instead
* Template updates
  * Simpler installation of the `nf-core` helper tool, now directly from PyPI
  * Bump minimum nextflow version to `0.32.0` - required for built in `manifest.nextflowVersion` check and access to `workflow.manifest` variables from within nextflow scripts
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
