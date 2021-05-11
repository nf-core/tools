# nf-core/tools: Changelog

## [v1.14 - Brass Chicken :chicken:](https://github.com/nf-core/tools/releases/tag/1.14) - [2021-05-11]

### Template

* Fixed an issue regarding explicit disabling of unused container engines [[#972](https://github.com/nf-core/tools/pull/972)]
* Removed trailing slash from `params.igenomes_base` to yield valid s3 paths (previous paths work with Nextflow but not aws cli)
* Added a timestamp to the trace + timetime + report + dag filenames to fix overwrite issue on AWS
* Rewrite the `params_summary_log()` function to properly ignore unset params and have nicer formatting [[#971](https://github.com/nf-core/tools/issues/971)]
* Fix overly strict `--max_time` formatting regex in template schema [[#973](https://github.com/nf-core/tools/issues/973)]
* Convert `d` to `day` in the `cleanParameters` function to make Duration objects like `2d` pass the validation [[#858](https://github.com/nf-core/tools/issues/858)]
* Added nextflow version to quick start section and adjusted `nf-core bump-version` [[#1032](https://github.com/nf-core/tools/issues/1032)]
* Use latest stable Nextflow version `21.04.0` for CI tests instead of the `-edge` release

### Download

* Fix bug in `nf-core download` where image names were getting a hyphen in `nf-core` which was breaking things.
* Extensive new interactive prompts for all command line flags [[#1027](https://github.com/nf-core/tools/issues/1027)]
  * It is now recommended to run `nf-core download` without any cli options and follow prompts (though flags can be used to run non-interactively if you wish)
* New helper code to set `$NXF_SINGULARITY_CACHEDIR` and add to `.bashrc` if desired [[#1027](https://github.com/nf-core/tools/issues/1027)]

### Launch

* Strip values from `nf-core launch` web response which are `False` and have no default in the schema [[#976](https://github.com/nf-core/tools/issues/976)]
* Improve API caching code when polling the website, fixes noisy log message when waiting for a response [[#1029](https://github.com/nf-core/tools/issues/1029)]
* New interactive prompts for pipeline name [[#1027](https://github.com/nf-core/tools/issues/1027)]

### Modules

* Added `tool_name_underscore` to the module template to allow TOOL_SUBTOOL in `main.nf` [[#1011](https://github.com/nf-core/tools/issues/1011)]
* Added `--conda-name` flag to `nf-core modules create` command to allow sidestepping questionary [[#988](https://github.com/nf-core/tools/issues/988)]
* Extended `nf-core modules lint` functionality to check tags in `test.yml` and to look for a entry in the `pytest_software.yml` file
* Update `modules` commands to use new test tag format `tool/subtool`
* New modules lint test comparing the `functions.nf` file to the template version
* Modules installed from alternative sources are put in folders based on the name of the source repository

### Linting

* Fix bug in nf-core lint config skipping for the `nextflow_config` test [[#1019](https://github.com/nf-core/tools/issues/1019)]
* New `-k`/`--key` cli option for `nf-core lint` to allow you to run only named lint tests, for faster local debugging
* Merge markers lint test - ignore binary files, allow config to ignore specific files [[#1040](https://github.com/nf-core/tools/pull/1040)]
* New lint test to check if all defined pipeline parameters are mentioned in `main.nf` [[#1038](https://github.com/nf-core/tools/issues/1038)]
* Added fix to remove warnings about params that get converted from camelCase to camel-case [[#1035](https://github.com/nf-core/tools/issues/1035)]
* Added pipeline schema lint checks for missing parameter description and parameters outside of groups [[#1017](https://github.com/nf-core/tools/issues/1017)]

### General

* Try to fix the fix for the automated sync when we submit too many PRs at once [[#970](https://github.com/nf-core/tools/issues/970)]
* Rewrite how the tools documentation is deployed to the website, to allow multiple versions
* Created new Docker image for the tools cli package - see installation docs for details [[#917](https://github.com/nf-core/tools/issues/917)]
* Ignore permission errors for setting up requests cache directories to allow starting with an invalid or read-only `HOME` directory

## [v1.13.3 - Copper Crocodile Resurrection :crocodile:](https://github.com/nf-core/tools/releases/tag/1.13.2) - [2021-03-24]

* Running tests twice with `nf-core modules create-test-yml` to catch unreproducible md5 sums [[#890](https://github.com/nf-core/tools/issues/890)]
* Fix sync error again where the Nextflow edge release needs to be used for some pipelines
* Fix bug with `nf-core lint --release` (`NameError: name 'os' is not defined`)
* Added linebreak to linting comment so that markdown header renders on PR comment properly
* `nf-core modules create` command - if no bioconda package is found, prompt user for a different bioconda package name
* Updated module template `main.nf` with new test data paths

## [v1.13.2 - Copper Crocodile CPR :crocodile: :face_with_head_bandage:](https://github.com/nf-core/tools/releases/tag/1.13.2) - [2021-03-23]

* Make module template pass the EC linter [[#953](https://github.com/nf-core/tools/pull/953)]
* Added better logging message if a user doesn't specificy the directory correctly with `nf-core modules` commands [[#942](https://github.com/nf-core/tools/pull/942)]
* Fixed parameter validation bug caused by JSONObject [[#937](https://github.com/nf-core/tools/issues/937)]
* Fixed template creation error regarding file permissions [[#932](https://github.com/nf-core/tools/issues/932)]
* Split the `create-lint-wf` tests up into separate steps in GitHub Actions to make the CI results easier to read
* Added automated PR comments to the Markdown, YAML and Python lint CI tests to explain failures (tools and pipeline template)
* Make `nf-core lint` summary table borders coloured according to overall pass / fail status
* Attempted a fix for the automated sync when we submit too many PRs at once [[#911](https://github.com/nf-core/tools/issues/911)]

## [v1.13.1 - Copper Crocodile Patch :crocodile: :pirate_flag:](https://github.com/nf-core/tools/releases/tag/1.13.1) - [2021-03-19]

* Fixed bug in pipeline linting markdown output that gets posted to PR comments [[#914]](https://github.com/nf-core/tools/issues/914)
* Made text for the PR branch CI check less verbose with a TLDR in bold at the top
* A number of minor tweaks to the new `nf-core modules lint` code

## [v1.13 - Copper Crocodile](https://github.com/nf-core/tools/releases/tag/1.13) - [2021-03-18]

### Template

* **Major new feature** - Validation of pipeline parameters [[#426]](https://github.com/nf-core/tools/issues/426)
  * The addition runs as soon as the pipeline launches and checks the pipeline input parameters two main things:
    * No parameters are supplied that share a name with core Nextflow options (eg. `--resume` instead of `-resume`)
    * Supplied parameters validate against the pipeline JSON schema (eg. correct variable types, required values)
  * If either parameter validation fails or the pipeline has errors, a warning is given about any unexpected parameters found which are not described in the pipeline schema.
  * This behaviour can be disabled by using `--validate_params false`
* Added profiles to support the [Charliecloud](https://hpc.github.io/charliecloud/) and [Shifter](https://nersc.gitlab.io/development/shifter/how-to-use/) container engines [[#824](https://github.com/nf-core/tools/issues/824)]
  * Note that Charliecloud requires Nextflow version `v21.03.0-edge` or later.
* Profiles for container engines now explicitly _disable_ all other engines [[#867](https://github.com/nf-core/tools/issues/867)]
* Fixed typo in nf-core-lint CI that prevented the markdown summary from being automatically posted on PRs as a comment.
* Changed default for `--input` from `data/*{1,2}.fastq.gz` to `null`, as this is now validated by the schema as a required value.
* Removed support for `--name` parameter for custom run names.
  * The same functionality for MultiQC still exists with the core Nextflow `-name` option.
* Added to template docs about how to identify process name for resource customisation
* The parameters `--max_memory` and `--max_time` are now validated against a regular expression [[#793](https://github.com/nf-core/tools/issues/793)]
  * Must be written in the format `123.GB` / `456.h` with any of the prefixes listed in the [Nextflow docs](https://www.nextflow.io/docs/latest/process.html#memory)
  * Bare numbers no longer allowed, avoiding people from trying to specify GB and actually specifying bytes.
* Switched from cookiecutter to Jinja2 [[#880]](https://github.com/nf-core/tools/pull/880)
* Finally dropped the wonderful [cookiecutter](https://github.com/cookiecutter/cookiecutter) library that was behind the first pipeline template that led to nf-core [[#880](https://github.com/nf-core/tools/pull/880)]
  * Now rendering templates directly using [Jinja](https://jinja.palletsprojects.com/), which is what cookiecutter was doing anyway

### Modules

Initial addition of a number of new helper commands for working with DSL2 modules:

* `modules list` - List available modules
* `modules install` - Install a module from nf-core/modules
* `modules remove` - Remove a module from a pipeline
* `modules create` - Create a module from the template
* `modules create-test-yml` - Create the `test.yml` file for a module with md5 sums, tags, commands and names added
* `modules lint` - Check a module against nf-core guidelines

You can read more about each of these commands in the main tools documentation (see `README.md` or <https://nf-co.re/tools>)

### Tools helper code

* Fixed some bugs in the command line interface for `nf-core launch` and improved formatting [[#829](https://github.com/nf-core/tools/pull/829)]
* New functionality for `nf-core download` to make it compatible with DSL2 pipelines [[#832](https://github.com/nf-core/tools/pull/832)]
  * Singularity images in module files are now discovered and fetched
  * Direct downloads of Singularity images in python allowed (much faster than running `singularity pull`)
  * Downloads now work with `$NXF_SINGULARITY_CACHEDIR` so that pipelines sharing containers have efficient downloads
* Changed behaviour of `nf-core sync` command [[#787](https://github.com/nf-core/tools/issues/787)]
  * Instead of opening or updating a PR from `TEMPLATE` directly to `dev`, a new branch is now created from `TEMPLATE` and a PR opened from this to `dev`.
  * This is to make it easier to fix merge conflicts without accidentally bringing the entire pipeline history back into the `TEMPLATE` branch (which makes subsequent sync merges much more difficult)

### Linting

* Major refactor and rewrite of pipieline linting code
  * Much better code organisation and maintainability
  * New automatically generated documentation using Sphinx
  * Numerous new tests and functions, removal of some unnecessary tests
* Added lint check for merge markers [[#321]](https://github.com/nf-core/tools/issues/321)
* Added new option `--fix` to automatically correct some problems detected by linting
* Added validation of default params to `nf-core schema lint` [[#823](https://github.com/nf-core/tools/issues/823)]
* Added schema validation of GitHub action workflows to lint function [[#795](https://github.com/nf-core/tools/issues/795)]
* Fixed bug in schema title and description validation
* Added second progress bar for conda dependencies lint check, as it can be slow [[#299](https://github.com/nf-core/tools/issues/299)]
* Added new lint test to check files that should be unchanged from the pipeline.
* Added the possibility to ignore lint tests using a `nf-core-lint.yml` config file [[#809](https://github.com/nf-core/tools/pull/809)]

## [v1.12.1 - Silver Dolphin](https://github.com/nf-core/tools/releases/tag/1.12.1) - [2020-12-03]

### Template

* Finished switch from `$baseDir` to `$projectDir` in `iGenomes.conf` and `main.nf`
  * Main fix is for `smail_fields` which was a bug introduced in the previous release. Sorry about that!
* Ported a number of small content tweaks from nf-core/eager to the template [[#786](https://github.com/nf-core/tools/issues/786)]
  * Better contributing documentation, more placeholders in documentation files, more relaxed markdownlint exceptions for certain HTML tags, more content for the PR and issue templates.

### Tools helper code

* Pipeline schema: make parameters of type `range` to `number`. [[#738](https://github.com/nf-core/tools/issues/738)]
* Respect `$NXF_HOME` when looking for pipelines with `nf-core list` [[#798](https://github.com/nf-core/tools/issues/798)]
* Swapped PyInquirer with questionary for command line questions in `launch.py` [[#726](https://github.com/nf-core/tools/issues/726)]
  * This should fix conda installation issues that some people had been hitting
  * The change also allows other improvements to the UI
* Fix linting crash when a file deleted but not yet staged in git [[#796](https://github.com/nf-core/tools/issues/796)]

## [v1.12 - Mercury Weasel](https://github.com/nf-core/tools/releases/tag/1.12) - [2020-11-19]

### Tools helper code

* Updated `nf_core` documentation generator for building [https://nf-co.re/tools-docs/](https://nf-co.re/tools-docs/)

### Template

* Make CI comments work with PRs from forks [[#765](https://github.com/nf-core/tools/issues/765)]
  * Branch protection and linting results should now show on all PRs
* Updated GitHub issue templates, which had stopped working
* Refactored GitHub Actions so that the AWS full-scale tests are triggered after docker build is finished
  * DockerHub push workflow split into two - one for dev, one for releases
* Updated actions to no longer use `set-env` which is now depreciating [[#739](https://github.com/nf-core/tools/issues/739)]
* Added config import for `test_full` in `nextflow.config`
* Switched depreciated `$baseDir` to `$projectDir`
* Updated minimum Nextflow version to `20.04.10`
* Make Nextflow installation less verbose in GitHub Actions [[#780](https://github.com/nf-core/tools/pull/780)]

### Linting

* Updated code to display colours in GitHub Actions log output
* Allow tests to pass with `dev` version of nf-core/tools (previous failure due to base image version)
* Lint code no longer tries to post GitHub PR comments. This is now done in a GitHub Action only.

## [v1.11 - Iron Tiger](https://github.com/nf-core/tools/releases/tag/1.11) - [2020-10-27]

### Template

* Fix command error in `awstest.yml` GitHub Action workflow.
* Allow manual triggering of AWS test GitHub Action workflows.
* Remove TODO item, which was proposing the usage of additional files beside `usage.md` and `output.md` for documentation.
* Added a Podman profile, which enables Podman as container.
* Updated linting for GitHub actions AWS tests workflows.

### Linting

* Made a base-level `Dockerfile` a warning instead of failure
* Added a lint failure if the old `bin/markdown_to_html.r` script is found
* Update `rich` package dependency and use new markup escaping to change `[[!]]` back to `[!]` again

### Other

* Pipeline sync - fetch full repo when checking out before sync
* Sync - Add GitHub actions manual trigger option

## [v1.10.2 - Copper Camel _(brought back from the dead)_](https://github.com/nf-core/tools/releases/tag/1.10.2) - [2020-07-31]

Second patch release to address some small errors discovered in the pipeline template.
Apologies for the inconvenience.

* Fix syntax error in `/push_dockerhub.yml` GitHub Action workflow
* Change `params.readPaths` -> `params.input_paths` in `test_full.config`
* Check results when posting the lint results as a GitHub comment
  * This feature is unfortunately not possible when making PRs from forks outside of the nf-core organisation for now.
* More major refactoring of the automated pipeline sync
  * New GitHub Actions matrix parallelisation of sync jobs across pipelines [[#673](https://github.com/nf-core/tools/issues/673)]
  * Removed the `--all` behaviour from `nf-core sync` as we no longer need it
  * Sync now uses a new list of pipelines on the website which does not include archived pipelines [[#712](https://github.com/nf-core/tools/issues/712)]
  * When making a PR it checks if a PR already exists - if so it updates it [[#710](https://github.com/nf-core/tools/issues/710)]
  * More tests and code refactoring for more stable code. Hopefully fixes 404 error [[#711](https://github.com/nf-core/tools/issues/711)]

## [v1.10.1 - Copper Camel _(patch)_](https://github.com/nf-core/tools/releases/tag/1.10.1) - [2020-07-30]

Patch release to fix the automatic template synchronisation, which failed in the v1.10 release.

* Improved logging: `nf-core --log-file log.txt` now saves a verbose log to disk.
* nf-core/tools GitHub Actions pipeline sync now uploads verbose log as an artifact.
* Sync - fixed several minor bugs, made logging less verbose.
* Python Rich library updated to `>=4.2.1`
* Hopefully fix git config for pipeline sync so that commit comes from @nf-core-bot
* Fix sync auto-PR text indentation so that it doesn't all show as code
* Added explicit flag `--show-passed` for `nf-core lint` instead of taking logging verbosity

## [v1.10 - Copper Camel](https://github.com/nf-core/tools/releases/tag/1.10) - [2020-07-30]

### Pipeline schema

This release of nf-core/tools introduces a major change / new feature: pipeline schema.
These are [JSON Schema](https://json-schema.org/) files that describe all of the parameters for a given
pipeline with their ID, a description, a longer help text, an optional default value, a variable _type_
(eg. `string` or `boolean`) and more.

The files will be used in a number of places:

* Automatic validation of supplied parameters when running pipelines
  * Pipeline execution can be immediately stopped if a required `param` is missing,
    or does not conform to the patterns / allowed values in the schema.
* Generation of pipeline command-line help
  * Running `nextflow run <pipeline> --help` will use the schema to generate a help text automatically
* Building online documentation on the [nf-core website](https://nf-co.re)
* Integration with 3rd party graphical user interfaces

To support these new schema files, nf-core/tools now comes with a new set of commands: `nf-core schema`.

* Pipeline schema can be generated or updated using `nf-core schema build` - this takes the parameters from
  the pipeline config file and prompts the developer for any mismatch between schema and pipeline.
  * Once a skeleton Schema file has been built, the command makes use of a new nf-core website tool to provide
    a user friendly graphical interface for developers to add content to their schema: [https://nf-co.re/pipeline_schema_builder](https://nf-co.re/pipeline_schema_builder)
* Pipelines will be automatically tested for valid schema that describe all pipeline parameters using the
  `nf-core schema lint` command (also included as part of the main `nf-core lint` command).
* Users can validate their set of pipeline inputs using the `nf-core schema validate` command.

In addition to the new schema commands, the `nf-core launch` command has been completely rewritten from
scratch to make use of the new pipeline schema. This command can use either an interactive command-line
prompt or a rich web interface to help users set parameters for a pipeline run.

The parameter descriptions and help text are fully used and embedded into the launch interfaces to make
this process as user-friendly as possible. We hope that it's particularly well suited to those new to nf-core.

Whilst we appreciate that this new feature will add a little work for pipeline developers, we're excited at
the possibilities that it brings. If you have any feedback or suggestions, please let us know either here on
GitHub or on the nf-core [`#json-schema` Slack channel](https://nfcore.slack.com/channels/json-schema).

### Python code formatting

We have adopted the use of the [Black Python code formatter](https://black.readthedocs.io/en/stable/).
This ensures a harmonised code formatting style throughout the package, from all contributors.
If you are editing any Python code in nf-core/tools you must now pass the files through Black when
making a pull-request. See [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md) for details.

### Template

* Add `--publish_dir_mode` parameter [#585](https://github.com/nf-core/tools/issues/585)
* Isolate R library paths to those in container [#541](https://github.com/nf-core/tools/issues/541)
* Added new style of pipeline parameters JSON schema to pipeline template
* Add ability to attach MultiQC reports to completion emails when using `mail`
* Update `output.md` and add in 'Pipeline information' section describing standard NF and pipeline reporting.
* Build Docker image using GitHub Actions, then push to Docker Hub (instead of building on Docker Hub)
* Add Slack channel badge in pipeline README
* Allow multiple container tags in `ci.yml` if performing multiple tests in parallel
* Add AWS CI tests and full tests GitHub Actions workflows
* Update AWS CI tests and full tests secrets names
* Added `macs_gsize` for danRer10, based on [this post](https://biostar.galaxyproject.org/p/18272/)
* Add information about config files used for workflow execution (`workflow.configFiles`) to summary
* Fix `markdown_to_html.py` to work with Python 2 and 3.
* Change `params.reads` -> `params.input`
* Change `params.readPaths` -> `params.input_paths`
* Added a `.github/.dockstore.yml` config file for automatic workflow registration with [dockstore.org](https://dockstore.org/)

### Linting

* Refactored PR branch tests to be a little clearer.
* Linting error docs explain how to add an additional branch protecton rule to the `branch.yml` GitHub Actions workflow.
* Adapted linting docs to the new PR branch tests.
* Failure for missing the readme bioconda badge is now a warn, in case this badge is not relevant
* Added test for template `{{ cookiecutter.var }}` placeholders
* Fix failure when providing version along with build id for Conda packages
* New `--json` and `--markdown` options to print lint results to JSON / markdown files
* Linting code now automatically posts warning / failing results to GitHub PRs as a comment if it can
* Added AWS GitHub Actions workflows linting
* Fail if `params.input` isn't defined.
* Beautiful new progress bar to look at whilst linting is running and awesome new formatted output on the command line :heart_eyes:
  * All made using the excellent [`rich` python library](https://github.com/willmcgugan/rich) - check it out!
* Tests looking for `TODO` strings should now ignore editor backup files. [#477](https://github.com/nf-core/tools/issues/477)

### nf-core/tools Continuous Integration

* Added CI test to check for PRs against `master` in tools repo
* CI PR branch tests fixed & now automatically add a comment on the PR if failing, explaining what is wrong
* Move some of the issue and PR templates into HTML `<!-- comments -->` so that they don't show in issues / PRs

### Other

* Describe alternative installation method via conda with `conda env create`
* nf-core/tools version number now printed underneath header artwork
* Bumped Conda version shipped with nfcore/base to 4.8.2
* Added log message when creating new pipelines that people should talk to the community about their plans
* Fixed 'on completion' emails sent using the `mail` command not containing body text.
* Improved command-line help text for nf-core/tools
* `nf-core list` now hides archived pipelines unless `--show_archived` flag is set
* Command line tools now checks if there is a new version of nf-core/tools available
  * Disable this by setting the environment variable `NFCORE_NO_VERSION_CHECK`, eg. `export NFCORE_NO_VERSION_CHECK=1`
* Better command-line output formatting of nearly all `nf-core` commands using [`rich`](https://github.com/willmcgugan/rich)

## [v1.9 - Platinum Pigeon](https://github.com/nf-core/tools/releases/tag/1.9) - [2020-02-20]

### Continuous integration

* Travis CI tests are now deprecated in favor of GitHub Actions within the pipeline template.
  * `nf-core bump-version` support has been removed for `.travis.yml`
  * `nf-core lint` now fails if a `.travis.yml` file is found
* Ported nf-core/tools Travis CI automation to GitHub Actions.
* Fixed the build for the nf-core/tools API documentation on the website

### Template

* Rewrote the documentation markdown > HTML conversion in Python instead of R
* Fixed rendering of images in output documentation [#391](https://github.com/nf-core/tools/issues/391)
* Removed the requirement for R in the conda environment
* Make `params.multiqc_config` give an _additional_ MultiQC config file instead of replacing the one that ships with the pipeline
* Ignore only `tests/` and `testing/` directories in `.gitignore` to avoid ignoring `test.config` configuration file
* Rephrase docs to promote usage of containers over Conda to ensure reproducibility
* Stage the workflow summary YAML file within MultiQC work directory

### Linting

* Removed linting for CircleCI
* Allow any one of `params.reads` or `params.input` or `params.design` before warning
* Added whitespace padding to lint error URLs
* Improved documentation for lint errors
* Allow either `>=` or `!>=` in nextflow version checks (the latter exits with an error instead of just warning) [#506](https://github.com/nf-core/tools/issues/506)
* Check that `manifest.version` ends in `dev` and throw a warning if not
  * If running with `--release` check the opposite and fail if not
* Tidied up error messages and syntax for linting GitHub actions branch tests
* Add YAML validator
* Don't print test results if we have a critical error

### Other

* Fix automatic synchronisation of the template after releases of nf-core/tools
* Improve documentation for installing `nf-core/tools`
* Replace preprint by the new nf-core publication in Nature Biotechnology :champagne:
* Use `stderr` instead of `stdout` for header artwork
* Tolerate unexpected output from `nextflow config` command
* Add social preview image
* Added a [release checklist](.github/RELEASE_CHECKLIST.md) for the tools repo

## [v1.8 - Black Sheep](https://github.com/nf-core/tools/releases/tag/1.8) - [2020-01-27]

### Continuous integration

* GitHub Actions CI workflows are now included in the template pipeline
  * Please update these files to match the existing tests that you have in `.travis.yml`
* Travis CI tests will be deprecated from the next `tools` release
* Linting will generate a warning if GitHub Actions workflows do not exist and if applicable to remove Travis CI workflow file i.e. `.travis.yml`.

### Tools helper code

* Refactored the template synchronisation code to be part of the main nf-core tool
* `nf-core bump-version` now also bumps the version string of the exported conda environment in the Dockerfile
* Updated Blacklist of synced pipelines
* Ignore pre-releases in `nf-core list`
* Updated documentation for `nf-core download`
* Fixed typo in `nf-core launch` final command
* Handle missing pipeline descriptions in `nf-core list`
* Migrate tools package CI to GitHub Actions

### Linting

* Adjusted linting to enable `patch` branches from being tested
* Warn if GitHub Actions workflows do not exist, warn if `.travis.yml` and circleCI are there
* Lint for `Singularity` file and raise error if found [#458](https://github.com/nf-core/tools/issues/458)
* Added linting of GitHub Actions workflows `linting.yml`, `ci.yml` and `branch.yml`
* Warn if pipeline name contains upper case letters or non alphabetical characters [#85](https://github.com/nf-core/tools/issues/85)
* Make CI tests of lint code pass for releases

### Template pipeline

* Fixed incorrect paths in iGenomes config as described in issue [#418](https://github.com/nf-core/tools/issues/418)
* Fixed incorrect usage of non-existent parameter in the template [#446](https://github.com/nf-core/tools/issues/446)
* Add UCSC genomes to `igenomes.config` and add paths to all genome indices
* Change `maxMultiqcEmailFileSize` parameter to `max_multiqc_email_size`
* Export conda environment in Docker file [#349](https://github.com/nf-core/tools/issues/349)
* Change remaining parameters from `camelCase` to `snake_case` [#39](https://github.com/nf-core/hic/issues/39)
  * `--singleEnd` to `--single_end`
  * `--igenomesIgnore` to `--igenomes_ignore`
  * Having the old camelCase versions of these will now throw an error
* Add `autoMounts=true` to default singularity profile
* Add in `markdownlint` checks that were being ignored by default
* Disable ansi logging in the travis CI tests
* Move `params`section from `base.config` to `nextflow.config`
* Use `env` scope to export `PYTHONNOUSERSITE` in `nextflow.config` to prevent conflicts with host Python environment
* Bump minimum Nextflow version to `19.10.0` - required to properly use `env` scope in `nextflow.config`
* Added support for nf-tower in the travis tests, using public mailbox nf-core@mailinator.com
* Add link to [Keep a Changelog](http://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](http://semver.org/spec/v2.0.0.html) to CHANGELOG
* Adjusted `.travis.yml` checks to allow for `patch` branches to be tested
* Add Python 3.7 dependency to the `environment.yml` file
* Remove `awsbatch` profile cf [nf-core/configs#71](https://github.com/nf-core/configs/pull/71)
* Make `scrape_software_versions.py` compatible with Python3 to enable miniconda3 in    [base image PR](https://github.com/nf-core/tools/pull/462)
* Add GitHub Actions workflows and respective linting
* Add `NXF_ANSI_LOG` as global environment variable to template GitHub Actions CI workflow
* Fixed global environment variable in GitHub Actions CI workflow
* Add `--awscli` parameter
* Add `README.txt` path for genomes in `igenomes.config` [nf-core/atacseq#75](https://github.com/nf-core/atacseq/issues/75)
* Fix buggy ANSI codes in pipeline summary log messages
* Add a `TODO` line in the new GitHub Actions CI test files

### Base Docker image

* Use miniconda3 instead of miniconda for a Python 3k base environment
  * If you still need Python 2 for your pipeline, add `conda-forge::python=2.7.4` to the dependencies in your `environment.yml`
* Update conda version to 4.7.12

### Other

* Updated Base Dockerfile to Conda 4.7.10
* Entirely switched from Travis-Ci.org to Travis-Ci.com for template and tools
* Improved core documentation (`-profile`)

## [v1.7 - Titanium Kangaroo](https://github.com/nf-core/tools/releases/tag/1.7) - [2019-10-07]

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
* The readme should now be rendered properly on PyPI.

### Syncing

* Can now sync a targeted pipeline via command-line
* Updated Blacklist of synced pipelines
* Removed `chipseq` from Blacklist of synced pipelines
* Fixed issue [#314](https://github.com/nf-core/tools/issues/314)

### Linting

* If the container slug does not contain the nf-core organisation (for example during development on a fork), linting will raise a warning, and an error with release mode on

### Template pipeline

* Add new code for Travis CI to allow PRs from patch branches too
* Fix small typo in central readme of tools for future releases
* Small code polishing + typo fix in the template main.nf file
* Header ANSI codes no longer print `[2m` to console when using `-with-ansi`
* Switched to yaml.safe_load() to fix PyYAML warning that was thrown because of a possible [exploit](https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation)
* Add `nf-core` citation
* Add proper `nf-core` logo for tools
* Add `Quick Start` section to main README of template
* Fix [Docker RunOptions](https://github.com/nf-core/tools/pull/351) to get UID and GID set in the template
* `Dockerfile` now specifically uses the proper release tag of the nfcore/base image
* Use [`file`](https://github.com/nf-core/tools/pull/354) instead of `new File`
  to avoid weird behavior such as making an `s3:/` directory locally when using
  an AWS S3 bucket as the `--outdir`.
* Fix workflow.onComplete() message when finishing pipeline
* Update URL for joining the nf-core slack to [https://nf-co.re/join/slack](https://nf-co.re/join/slack)
* Add GitHub Action for CI and Linting
* [Increased default time limit](https://github.com/nf-core/tools/issues/370) to 4h
* Add direct link to the pipeline slack channel in the contribution guidelines
* Add contributions and support heading with links to contribution guidelines and link to the pipeline slack channel in the main README
* Fix Parameters JSON due to new versionized structure
* Added conda-forge::r-markdown=1.1 and conda-forge::r-base=3.6.1 to environment
* Plain-text email template now has nf-core ASCII artwork
* Template configured to use logo fetched from website
* New option `--email_on_fail` which only sends emails if the workflow is not successful
* Add file existence check when checking software versions
* Fixed issue [#165](https://github.com/nf-core/tools/issues/165) - Use `checkIfExists`
* Consistent spacing for `if` statements
* Add sensible resource labels to `base.config`

### Other

* Bump `conda` to 4.6.14 in base nf-core Dockerfile
* Added a Code of Conduct to nf-core/tools, as only the template had this before
* TravisCI tests will now also start for PRs from `patch` branches, [to allow fixing critical issues](https://github.com/nf-core/tools/pull/392) without making a new major release

## [v1.6 - Brass Walrus](https://github.com/nf-core/tools/releases/tag/1.6) - [2020-04-09]

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

## [v1.5 - Iron Shark](https://github.com/nf-core/tools/releases/tag/1.5) - [2019-03-13]

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

## [v1.4 - Tantalum Butterfly](https://github.com/nf-core/tools/releases/tag/1.4) - [2018-12-12]

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

## [v1.3 - Citreous Swordfish](https://github.com/nf-core/tools/releases/tag/1.3) - [2018-11-21]

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

## [v1.2](https://github.com/nf-core/tools/releases/tag/1.2) - [2018-10-01]

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

## [v1.1](https://github.com/nf-core/tools/releases/tag/1.1) - [2018-08-14]

Very large release containing lots of work from the first nf-core hackathon, held in SciLifeLab Stockholm.

* The [Cookiecutter template](https://github.com/nf-core/cookiecutter) has been merged into tools
  * The old repo above has been archived
  * New pipelines are now created using the command `nf-core create`
  * The nf-core template and associated linting are now controlled under the same version system
* Large number of template updates and associated linting changes
  * New simplified cookiecutter variable usage
  * Refactored documentation - simplified and reduced duplication
  * Better `manifest` variables instead of `params` for pipeline name and version
  * New integrated nextflow version checking
  * Updated travis docker pull command to use tagging to allow release tests to pass
  * Reverted Docker and Singularity syntax to use `ENV` hack again
* Improved Python readme parsing for PyPI
* Updated Travis tests to check that the correct `dev` branch is being targeted
* New sync tool to automate pipeline updates
  * Once initial merges are complete, a nf-core bot account will create PRs for future template updates

## [v1.0.1](https://github.com/nf-core/tools/releases/tag/1.0.1) - [2018-07-18]

The version 1.0 of nf-core tools cannot be installed from PyPi. This patch fixes it, by getting rid of the requirements.txt plus declaring the dependent modules in the setup.py directly.

## [v1.0](https://github.com/nf-core/tools/releases/tag/1.0) - [2018-06-12]

Initial release of the nf-core helper tools package. Currently includes four subcommands:

* `nf-core list`: List nf-core pipelines with local info
* `nf-core download`: Download a pipeline and singularity container
* `nf-core lint`: Check pipeline against nf-core guidelines
* `nf-core release`: Update nf-core pipeline version number
