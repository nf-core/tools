# nf-core/tools: Changelog

## v1.7dev

### PyPI package description

* The readme should now be rendered properly on PyPI.

### Tools helper code

* The tools `create` command now sets up a `TEMPLATE` and a `dev` branch for syncing
* Fixed issue [379](https://github.com/nf-core/tools/issues/379)
* nf-core launch now uses stable parameter schema version 0.1.0
* Check that PR from patch or dev branch is acceptable by linting
* Made code compatible with Python 3.7
* The `download` command now also fetches institutional configs from nf-core/configs
* When listing pipelines, a nicer message is given for the rare case of a detached `HEAD` ref in a locally pulled pipeline. [#297](https://github.com/nf-core/tools/issues/297)
* The `download` command can now compress files into a single archive.
* `nf-core create` now fetches a logo for the pipeline from the nf-core website

### Syncing

* Can now sync a targeted pipeline via command-line
* Updated Blacklist of synced pipelines
* Removed `chipseq` from Blacklist of synced pipelines
* Fixed issue [#314](https://github.com/nf-core/tools/issues/314)

### Linting

* If the container slug does not contain the nf-core organisation (for example during development on a fork), linting will raise a warning, and an error with release mode on

### Template

* Add new code for Travis CI to allow PRs from patch branches too
* Fix small typo in central readme of tools for future releases
* Small code polishing + typo fix in the template main.nf file
* Switched to yaml.safe_load() to fix PyYAML warning that was thrown because of a possible [exploit](https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation)
* Add `nf-core` citation
* Add proper `nf-core` logo for tools
* Add `Quick Start` section to main README of template
* Fix [Docker RunOptions](https://github.com/nf-core/tools/pull/351) to get UID and GID set in the template
* Use [`file`](https://github.com/nf-core/tools/pull/354) instead of `new File`
  to avoid weird behavior such as making an `s3:/` directory locally when using
  an AWS S3 bucket as the `--outdir`.
* Fix workflow.onComplete() message when finishing pipeline
* Update URL for joining the nf-core slack to https://nf-co.re/join/slack
* [Increased default time limit](https://github.com/nf-core/tools/issues/370) to 4h
* Add direct link to the pipeline slack channel in the contribution guidelines
* Add contributions and support heading with links to contribution guidelines and link to the pipeline slack channel in the main README
* Fix Parameters JSON due to new versionized structure
* Added conda-forge::r-markdown=1.1 and conda-forge::r-base=3.6.1 to environment
* Plain-text email template now has nf-core ASCII artwork
* Template configured to use logo fetched from website
* New option `--email_on_fail` which only sends emails if the workflow is not successful

### Other

* Bump `conda` to 4.6.14 in base nf-core Dockerfile
* Added a Code of Conduct to nf-core/tools, as only the template had this before
* TravisCI tests will now also start for PRs from `patch` branches, [to allow fixing critical issues](https://github.com/nf-core/tools/pull/392) without making a new major release

## v1.6

### Syncing

* Code refactoring to make the script more readable
* No travis build failure anymore on sync errors
* More verbose logging

### Template pipeline

* awsbatch `work-dir` checking moved to nextflow itself. Removed unsatisfiable check in main.nf template.
* Fixed markdown linting
* Tools CI testing now runs markdown lint on compiled template pipeline
* Migrated large portions of documentation to the [nf-core website](https://github.com/nf-core/nf-co.re/pull/93)
* Removed Gitter references in `.github/` directories for `tools/` and pipeline template.
* Changed `scrape_software_versions.py` to output `.csv` file
* Added `export_plots` parameter to multiqc config
* Corrected some typos as listed [here](https://github.com/nf-core/tools/issues/348) to Guidelines

### Tools helper code

* Drop [nf-core/rnaseq](https://github.com/nf-core/rnaseq]) from `blacklist.json` to make template sync available
* Updated main help command to sort the subcommands in a more logical order
* Updated readme to describe the new `nf-core launch` command
* Fix bugs in `nf-core download`
  * The _latest_ release is now fetched by default if not specified
  * Downloaded pipeline files are now properly executable.
* Fixed bugs in `nf-core list`
  * Sorting now works again
  * Output is partially coloured (better highlighting out of date pipelines)
  * Improved documentation
* Fixed bugs in `nf-core lint`
  * The order of conda channels is now correct, avoiding occasional erroneous errors that packages weren't found ([#207](https://github.com/nf-core/tools/issues/207))
  * Allow edge versions in nf-core pipelines
* Add reporting of ignored errored process
  * As a solution for [#103](https://github.com/nf-core/tools/issues/103))
* Add Bowtie2 and BWA in iGenome config file template

## [v1.5](https://github.com/nf-core/tools/releases/tag/1.5) - 2019-03-13 Iron Shark

### Template pipeline

* Dropped Singularity file
* Summary now logs details of the cluster profile used if from [nf-core/configs](https://github.com/nf-core/configs)
* Dockerhub is used in favor of Singularity Hub for pulling when using the Singularity profile
* Changed default container tag from latest to dev
* Brought the logo to life
* Change the default filenames for the pipeline trace files
* Remote fetch of nf-core/configs profiles fails gracefully if offline
* Remove `params.container` and just directly define `process.container` now
* Completion email now includes MultiQC report if not too big
* `params.genome` is now checked if set, to ensure that it's a valid iGenomes key
* Together with nf-core/configs, helper function now checks hostname and suggests a valid config profile
* `awsbatch` executor requires the `tracedir` not to be set to an `s3` bucket.

### Tools helper code

* New `nf-core launch` command to interactively launch nf-core pipelines from command-line
  * Works with a `parameters.settings.json` file shipped with each pipeline
  * Discovers additional `params` from the pipeline dynamically
* Drop Python 3.4 support
* `nf-core list` now only shows a value for _"is local latest version"_ column if there is a local copy.
* Lint markdown formatting in automated tests
  * Added `markdownlint-cli` for checking Markdown syntax in pipelines and tools repo
* Syncing now reads from a `blacklist.json` in order to exclude pipelines from being synced if necessary.
* Added nf-core tools API description to assist developers with the classes and functions available.
  * Docs are automatically built by Travis CI and updated on the nf-co.re website.
* Introduced test for filtering remote workflows by keyword.
* Build tools python API docs
  * Use Travis job for api doc generation and publish

* `nf-core bump-version` now stops before making changes if the linting fails
* Code test coverage
  * Introduced test for filtering remote workflows by keyword
* Linting updates
  * Now properly searches for conda packages in default channels
  * Now correctly validates version pinning for packages from PyPI
  * Updates for changes to `process.container` definition

### Other

* Bump `conda` to 4.6.7 in base nf-core Dockerfile

## [v1.4](https://github.com/nf-core/tools/releases/tag/1.4) - 2018-12-12 Tantalum Butterfly

### Template pipeline

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

### Tools helper code

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
