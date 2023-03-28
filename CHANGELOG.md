# nf-core/tools: Changelog

# v2.8dev

### Template

- Turn on automatic clean up of intermediate files in `work/` on successful pipeline completion in full-test config ([#2163](https://github.com/nf-core/tools/pull/2163)) [Contributed by @jfy133]
- Add documentation to `usage.md` on how to use `params.yml` files, based on nf-core/ampliseq text ([#2173](https://github.com/nf-core/tools/pull/2173/)) [Contributed by @jfy133, @d4straub]
- Make jobs automatically resubmit for a much wider range of exit codes (now `104` and `130..145`) ([#2170](https://github.com/nf-core/tools/pull/2170))
- Remove problematic sniffer code in samplesheet_check.py that could give false positive 'missing header' errors ([https://github.com/nf-core/tools/pull/2194]) [Contributed by @Midnighter, @jfy133]
- Consistent syntax for branch checks in PRs ([#2202](https://github.com/nf-core/tools/issues/2202))
- Fixed minor Jinja2 templating bug that caused the PR template to miss a newline

### Linting

### Modules

- Add an `--empty-template` option to create a module without TODO statements or examples ([#2175](https://github.com/nf-core/tools/pull/2175) & [#2177](https://github.com/nf-core/tools/pull/2177))

### Subworkflows

- Fixing problem when a module included in a subworkflow had a name change from TOOL to TOOL/SUBTOOL ([#2177](https://github.com/nf-core/tools/pull/2177))
- Fix `nf-core subworkflows test` not running subworkflow tests ([#2181](https://github.com/nf-core/tools/pull/2181))

### General

- `nf-core modules/subworkflows info` now prints the include statement for the module/subworkflow ([#2182](https://github.com/nf-core/tools/pull/2182)).

## [v2.7.2 - Mercury Eagle Patch](https://github.com/nf-core/tools/releases/tag/2.7.2) - [2022-12-19]

### Template

- Fix the syntax of github_output in GitHub actions ([#2114](https://github.com/nf-core/tools/pull/2114))
- Fix a bug introduced in 2.7 that made pipelines hang ([#2132](https://github.com/nf-core/tools/issues/2132))
- Explicitly disable `conda` when a container profile ([#2140](https://github.com/nf-core/tools/pull/2140))

### Linting

- Allow specifying containers in less than three lines ([#2121](https://github.com/nf-core/tools/pull/2121))
- Run prettier after dumping a json schema file ([#2124](https://github.com/nf-core/tools/pull/2124))

### General

- Only check that a pipeline name doesn't contain dashes if the name is provided by prompt of `--name`. Don't check if a template file is used. ([#2123](https://github.com/nf-core/tools/pull/2123))
- Deprecate `--enable_conda` parameter. Use `conda.enable` instead ([#2131](https://github.com/nf-core/tools/pull/2131))
- Handle `json.load()` exceptions ([#2134](https://github.com/nf-core/tools/pull/2134))
- Deprecate Python 3.7 support because it reaches EOL ([#2210](https://github.com/nf-core/tools/pull/2210))

## [v2.7.1 - Mercury Eagle Patch](https://github.com/nf-core/tools/releases/tag/2.7.1) - [2022-12-08]

- Patch release to fix pipeline sync ([#2110](https://github.com/nf-core/tools/pull/2110))

## [v2.7 - Mercury Eagle](https://github.com/nf-core/tools/releases/tag/2.7) - [2022-12-07]

Another big release with lots of new features and bug fixes. Thanks to all contributors!

**Highlights**

- New `nf-core subworkflows` subcommand for creating, removing, testing, updating and finding subworkflows, see the [documentation](https://nf-co.re/tools/#subworkflows) for more information.
- Every pipeline has now it's own GitHub codespace template, which can be used to develop the pipeline directly in the browser.
- Improved handling of modules and subworkflows from other repos than nf-core/modules.
- Pre-commit is now installed as a dependency, which allows us, besides other things, to run prettier on the fly even if it is not manually installed.
- Shell completion for nf-core commands, more information [here](https://nf-co.re/tools#shell-completion).

### Template

#### Features

- Ignore files in `bin/` directory when running prettier ([#2080](https://github.com/nf-core/tools/pull/1957)).
- Add GitHub codespaces template ([#1957](https://github.com/nf-core/tools/pull/1957))
- `nextflow run <pipeline> --version` will now print the workflow version from the manifest and exit ([#1951](https://github.com/nf-core/tools/pull/1951)).
- Add profile for running `docker` with the ARM chips (including Apple silicon) ([#1942](https://github.com/nf-core/tools/pull/1942) and [#2034](https://github.com/nf-core/tools/pull/2034)).
- Flip execution order of parameter summary printing and parameter validation to prevent 'hiding' of parameter errors ([#2033](https://github.com/nf-core/tools/pull/2033)).
- Change colour of 'pipeline completed successfully, but some processes failed' from red to yellow ([#2096](https://github.com/nf-core/tools/pull/2096)).

#### Bug fixes

- Fix lint warnings for `samplesheet_check.nf` module ([#1875](https://github.com/nf-core/tools/pull/1875)).
- Check that the workflow name provided with a template doesn't contain dashes ([#1822](https://github.com/nf-core/tools/pull/1822))
- Remove `CITATION.cff` file from pipeline template, to avoid that pipeline Zenodo entries reference the nf-core publication instead of the pipeline ([#2059](https://github.com/nf-core/tools/pull/2059)).- Add initial CHM13 support ([1988](https://github.com/nf-core/tools/issues/1988))
- Add initial CHM13 support ([1988](https://github.com/nf-core/tools/issues/1988))

### Linting

#### Features

- Add `--sort-by` option to linting which allows ordering module lint warnings/errors by either test name or module name ([#2077](https://github.com/nf-core/tools/pull/2077)).

#### Bug fixes

- Don't lint pipeline name if `manifest.name` in `.nf-core.yml` ([#2035](https://github.com/nf-core/tools/pull/2035))
- Don't check for `docker pull` commands in `actions_ci` lint test (leftover from DSL1) ([#2055](https://github.com/nf-core/tools/pull/2055)).

### General

#### Features

- Use pre-commit run prettier if prettier is not available ([#1983](https://github.com/nf-core/tools/pull/1983)) and initialize pre-commit in gitpod and codespaces ([#1957](https://github.com/nf-core/tools/pull/1957)).
- Refactor CLI flag `--hide-progress` to be at the top-level group, like `--verbose` ([#2016](https://github.com/nf-core/tools/pull/2016))
- `nf-core sync` now supports the template YAML file using `-t/--template-yaml` ([#1880](https://github.com/nf-core/tools/pull/1880)).
- The default branch can now be specified when creating a new pipeline repo [#1959](https://github.com/nf-core/tools/pull/1959).
- Only warn when checking that the pipeline directory contains a `main.nf` and a `nextflow.config` file if the pipeline is not an nf-core pipeline [#1964](https://github.com/nf-core/tools/pull/1964)
- Bump promoted Python version from 3.7 to 3.8 ([#1971](https://github.com/nf-core/tools/pull/1971)).
- Extended the chat notifications to Slack ([#1829](https://github.com/nf-core/tools/pull/1829)).
- Don't print source file + line number on logging messages (except when verbose) ([#2015](https://github.com/nf-core/tools/pull/2015))
- Automatically format `test.yml` content with Prettier ([#2078](https://github.com/nf-core/tools/pull/2078))
- Automatically format `modules.json` content with Prettier ([#2074](https://github.com/nf-core/tools/pull/2074))
- Add shell completion for nf-core tools commands([#2070](https://github.com/nf-core/tools/pull/2070))

#### Bug fixes, maintenance and tests

- Fix error in tagging GitPod docker images during releases ([#1874](https://github.com/nf-core/tools/pull/1874)).
- Fix bug when updating modules from old version in old folder structure ([#1908](https://github.com/nf-core/tools/pull/1908)).
- Don't remove local copy of modules repo, only update it with fetch ([#1881](https://github.com/nf-core/tools/pull/1881)).
- Improve test coverage of `sync.py` and `__main__.py` ([#1936](https://github.com/nf-core/tools/pull/1936), [#1965](https://github.com/nf-core/tools/pull/1965)).
- Add file `versions.yml` when generating `test.yml` with `nf-core modules create-test-yml` but don't check for md5sum [#1963](https://github.com/nf-core/tools/pull/1963).
- Mock biocontainers and anaconda api calls in modules and subworkflows tests [#1967](https://github.com/nf-core/tools/pull/1967)
- Run tests with Python 3.11 ([#1970](https://github.com/nf-core/tools/pull/1970)).
- Run test with a realistic version of git ([#2043](https://github.com/nf-core/tools/pull/2043)).
- Fix incorrect file deletion in `nf-core launch` when `--params_in` has the same name as `--params_out` ([#1986](https://github.com/nf-core/tools/pull/1986)).
- Updated GitHub actions ([#1998](https://github.com/nf-core/tools/pull/1998), [#2001](https://github.com/nf-core/tools/pull/2001))
- Code maintenance ([#1818](https://github.com/nf-core/tools/pull/1818), [#2032](https://github.com/nf-core/tools/pull/2032), [#2073](https://github.com/nf-core/tools/pull/2073)).
- Track from where modules and subworkflows are installed ([#1999](https://github.com/nf-core/tools/pull/1999)).
- Substitute ModulesCommand and SubworkflowsCommand by ComponentsCommand ([#2000](https://github.com/nf-core/tools/pull/2000)).
- Prevent installation with unsupported Python versions ([#2075](https://github.com/nf-core/tools/pull/2075)).
- Allow other remote URLs not starting with `http` ([#2061](https://github.com/nf-core/tools/pull/2061))

### Modules

- Update patch file paths if the modules directory has the old structure ([#1878](https://github.com/nf-core/tools/pull/1878)).
- Don't write to `modules.json` file when applying a patch file during `nf-core modules update` ([#2017](https://github.com/nf-core/tools/pull/2017)).

### Subworkflows

- Add subworkflow commands `create-test-yml`, `create` and `install` ([#1897](https://github.com/nf-core/tools/pull/1897)).
- Update subworkflows install so it installs also imported modules and subworkflows ([#1904](https://github.com/nf-core/tools/pull/1904)).
- `check_up_to_date()` function from `modules_json.py` also checks for subworkflows ([#1934](https://github.com/nf-core/tools/pull/1934)).
- Add tests for `nf-core subworkflows install` command ([#1996](https://github.com/nf-core/tools/pull/1996)).
- Function `create()` from `modules_json.py` adds also subworkflows to `modules.json` file ([#2005](https://github.com/nf-core/tools/pull/2005)).
- Add `nf-core subworkflows update` command ([#2019](https://github.com/nf-core/tools/pull/2019)).

## [v2.6 - Tin Octopus](https://github.com/nf-core/tools/releases/tag/2.6) - [2022-10-04]

### Template

- Add template for subworkflows
- Add `actions/upload-artifact` step to the awstest workflows, to expose the debug log file
- Add `prettier` as a requirement to Gitpod Dockerimage
- Bioconda incompatible conda channel setups now result in more informative error messages ([#1812](https://github.com/nf-core/tools/pull/1812))
- Improve template customisation documentation ([#1821](https://github.com/nf-core/tools/pull/1821))
- Update MultiQC module, update supplying MultiQC default and custom config and logo files to module
- Add a 'recommend' methods description text to MultiQC to help pipeline users report pipeline usage in publications ([#1749](https://github.com/nf-core/tools/pull/1749))
- Fix template spacing modified by JINJA ([#1830](https://github.com/nf-core/tools/pull/1830))
- Fix MultiQC execution on template ([#1855](https://github.com/nf-core/tools/pull/1855))
- Don't skip including `base.config` when skipping nf-core/configs

### Linting

- Pipelines: Check that the old renamed `lib` files are not still present:
  - `Checks.groovy` -> `Utils.groovy`
  - `Completion.groovy` -> `NfcoreTemplate.groovy`
  - `Workflow.groovy` -> `WorkflowMain.groovy`

### General

- Add function to enable chat notifications on MS Teams, accompanied by `hook_url` param to enable it.
- Schema: Remove `allOf` if no definition groups are left.
- Use contextlib to temporarily change working directories ([#1819](https://github.com/nf-core/tools/pull/1819))
- More helpful error messages if `nf-core download` can't parse a singularity image download
- Add `nf-core subworkflows create` command

### Modules

- If something is wrong with the local repo cache, offer to delete it and try again ([#1850](https://github.com/nf-core/tools/issues/1850))
- Restructure code to work with the directory restructuring in [modules](https://github.com/nf-core/modules/pull/2141) ([#1859](https://github.com/nf-core/tools/pull/1859))
- Make `label: process_single` default when creating a new module

## [v2.5.1 - Gold Otter Patch](https://github.com/nf-core/tools/releases/tag/2.5.1) - [2022-08-31]

- Patch release to fix black linting in pipelines ([#1789](https://github.com/nf-core/tools/pull/1789))
- Add isort options to pyproject.toml ([#1792](https://github.com/nf-core/tools/pull/1792))
- Lint pyproject.toml file exists and content ([#1795](https://github.com/nf-core/tools/pull/1795))
- Update GitHub PyPI package release action to v1 ([#1785](https://github.com/nf-core/tools/pull/1785))

### Template

- Update GitHub actions to use nodejs16 ([#1944](https://github.com/nf-core/tools/pull/1944))

## [v2.5 - Gold Otter](https://github.com/nf-core/tools/releases/tag/2.5) - [2022-08-30]

### Template

- Bumped Python version to 3.7 in the GitHub linting in the workflow template ([#1680](https://github.com/nf-core/tools/pull/1680))
- Fix bug in pipeline readme logo URL ([#1590](https://github.com/nf-core/tools/pull/1590))
- Switch CI to use [setup-nextflow](https://github.com/nf-core/setup-nextflow) action to install Nextflow ([#1650](https://github.com/nf-core/tools/pull/1650))
- Add `CITATION.cff` [#361](https://github.com/nf-core/tools/issues/361)
- Add Gitpod and Mamba profiles to the pipeline template ([#1673](https://github.com/nf-core/tools/pull/1673))
- Remove call to `getGenomeAttribute` in `main.nf` when running `nf-core create` without iGenomes ([#1670](https://github.com/nf-core/tools/issues/1670))
- Make `nf-core create` fail if Git default branch name is dev or TEMPLATE ([#1705](https://github.com/nf-core/tools/pull/1705))
- Convert `console` snippets to `bash` snippets in the template where applicable ([#1729](https://github.com/nf-core/tools/pull/1729))
- Add `branch` field to module entries in `modules.json` to record what branch a module was installed from ([#1728](https://github.com/nf-core/tools/issues/1728))
- Add customisation option to remove all GitHub support with `nf-core create` ([#1766](https://github.com/nf-core/tools/pull/1766))

### Linting

- Check that the `.prettierignore` file exists and that starts with the same content.
- Update `readme.py` nf version badge validation regexp to accept any signs before version number ([#1613](https://github.com/nf-core/tools/issues/1613))
- Add isort configuration and GitHub workflow ([#1538](https://github.com/nf-core/tools/pull/1538))
- Use black also to format python files in workflows ([#1563](https://github.com/nf-core/tools/pull/1563))
- Add check for mimetype in the `input` parameter. ([#1647](https://github.com/nf-core/tools/issues/1647))
- Check that the singularity and docker tags are parsable. Add `--fail-warned` flag to `nf-core modules lint` ([#1654](https://github.com/nf-core/tools/issues/1654))
- Handle exception in `nf-core modules lint` when process name doesn't start with process ([#1733](https://github.com/nf-core/tools/issues/1733))

### General

- Remove support for Python 3.6 ([#1680](https://github.com/nf-core/tools/pull/1680))
- Add support for Python 3.9 and 3.10 ([#1680](https://github.com/nf-core/tools/pull/1680))
- Invoking Python with optimizations no longer affects the program control flow ([#1685](https://github.com/nf-core/tools/pull/1685))
- Update `readme` to drop `--key` option from `nf-core modules list` and add the new pattern syntax
- Add `--fail-warned` flag to `nf-core lint` to make warnings fail ([#1593](https://github.com/nf-core/tools/pull/1593))
- Add `--fail-warned` flag to pipeline linting workflow ([#1593](https://github.com/nf-core/tools/pull/1593))
- Updated the nf-core package requirements ([#1620](https://github.com/nf-core/tools/pull/1620), [#1757](https://github.com/nf-core/tools/pull/1757), [#1756](https://github.com/nf-core/tools/pull/1756))
- Remove dependency of the mock package and use unittest.mock instead ([#1696](https://github.com/nf-core/tools/pull/1696))
- Fix and improve broken test for Singularity container download ([#1622](https://github.com/nf-core/tools/pull/1622))
- Use [`$XDG_CACHE_HOME`](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) or `~/.cache` instead of `$XDG_CONFIG_HOME` or `~/config/` as base directory for API cache
- Switch CI to use [setup-nextflow](https://github.com/nf-core/setup-nextflow) action to install Nextflow ([#1650](https://github.com/nf-core/tools/pull/1650))
- Add tests for `nf-core modules update` and `ModulesJson`.
- Add CI for GitLab remote [#1646](https://github.com/nf-core/tools/issues/1646)
- Add `CITATION.cff` [#361](https://github.com/nf-core/tools/issues/361)
- Allow customization of the `nf-core` pipeline template when using `nf-core create` ([#1548](https://github.com/nf-core/tools/issues/1548))
- Add Refgenie integration: updating of nextflow config files with a refgenie database ([#1090](https://github.com/nf-core/tools/pull/1090))
- Fix `--key` option in `nf-core lint` when supplying a module lint test name ([#1681](https://github.com/nf-core/tools/issues/1681))
- Add `no_git=True` when creating a new pipeline and initialising a git repository is not needed in `nf-core lint` and `nf-core bump-version` ([#1709](https://github.com/nf-core/tools/pull/1709))
- Move `strip_ansi_code` function in lint to `utils.py`
- Simplify control flow and don't use equality comparison for `None` and booleans
- Replace use of the deprecated `distutils` Version object with that from `packaging` ([#1735](https://github.com/nf-core/tools/pull/1735))
- Add code to cancel CI run if a new run starts ([#1760](https://github.com/nf-core/tools/pull/1760))
- CI for the API docs generation now uses the ubuntu-latest base image ([#1762](https://github.com/nf-core/tools/pull/1762))
- Add option to hide progress bars in `nf-core lint` and `nf-core modules lint` with `--hide-progress`.

### Modules

- Add `--fix-version` flag to `nf-core modules lint` command to update modules to the latest version ([#1588](https://github.com/nf-core/tools/pull/1588))
- Fix a bug in the regex extracting the version from biocontainers URLs ([#1598](https://github.com/nf-core/tools/pull/1598))
- Update how we interface with git remotes. ([#1626](https://github.com/nf-core/tools/issues/1626))
- Add prompt for module name to `nf-core modules info` ([#1644](https://github.com/nf-core/tools/issues/1644))
- Update docs with example of custom git remote ([#1645](https://github.com/nf-core/tools/issues/1645))
- Command `nf-core modules test` obtains module name suggestions from installed modules ([#1624](https://github.com/nf-core/tools/pull/1624))
- Add `--base-path` flag to `nf-core modules` to specify the base path for the modules in a remote. Also refactored `modules.json` code. ([#1643](https://github.com/nf-core/tools/issues/1643)) Removed after ([#1754](https://github.com/nf-core/tools/pull/1754))
- Rename methods in `ModulesJson` to remove explicit reference to `modules.json`
- Fix inconsistencies in the `--save-diff` flag `nf-core modules update`. Refactor `nf-core modules update` ([#1536](https://github.com/nf-core/tools/pull/1536))
- Fix bug in `ModulesJson.check_up_to_date` causing it to ask for the remote of local modules
- Handle errors when updating module version with `nf-core modules update --fix-version` ([#1671](https://github.com/nf-core/tools/pull/1671))
- Make `nf-core modules update --save-diff` work when files were created or removed ([#1694](https://github.com/nf-core/tools/issues/1694))
- Get the latest common build for Docker and Singularity containers of a module ([#1702](https://github.com/nf-core/tools/pull/1702))
- Add short option for `--no-pull` option in `nf-core modules`
- Add `nf-core modules patch` command ([#1312](https://github.com/nf-core/tools/issues/1312))
- Add support for patch in `nf-core modules update` command ([#1312](https://github.com/nf-core/tools/issues/1312))
- Add support for patch in `nf-core modules lint` command ([#1312](https://github.com/nf-core/tools/issues/1312))
- Add support for custom remotes in `nf-core modules lint` ([#1715](https://github.com/nf-core/tools/issues/1715))
- Make `nf-core modules` commands work with arbitrary git remotes ([#1721](https://github.com/nf-core/tools/issues/1721))
- Add links in `README.md` for `info` and `patch` commands ([#1722](https://github.com/nf-core/tools/issues/1722)])
- Fix misc. issues with `--branch` and `--base-path` ([#1726](https://github.com/nf-core/tools/issues/1726))
- Add `branch` field to module entries in `modules.json` to record what branch a module was installed from ([#1728](https://github.com/nf-core/tools/issues/1728))
- Fix broken link in `nf-core modules info`([#1745](https://github.com/nf-core/tools/pull/1745))
- Fix unbound variable issues and minor refactoring [#1742](https://github.com/nf-core/tools/pull/1742/)
- Recreate modules.json file instead of complaining about incorrectly formatted file. ([#1741](https://github.com/nf-core/tools/pull/1741)
- Add support for patch when creating `modules.json` file ([#1752](https://github.com/nf-core/tools/pull/1752))

## [v2.4.1 - Cobolt Koala Patch](https://github.com/nf-core/tools/releases/tag/2.4) - [2022-05-16]

- Patch release to try to fix the template sync ([#1585](https://github.com/nf-core/tools/pull/1585))
- Avoid persistent temp files from pytests ([#1566](https://github.com/nf-core/tools/pull/1566))
- Add option to trigger sync manually on just nf-core/testpipeline

## [v2.4 - Cobolt Koala](https://github.com/nf-core/tools/releases/tag/2.4) - [2022-05-16]

### Template

- Read entire lines when sniffing the samplesheet format (fix [#1561](https://github.com/nf-core/tools/issues/1561))
- Add actions workflow to respond to `@nf-core-bot fix linting` comments on pipeline PRs
- Fix Prettier formatting bug in completion email HTML template ([#1509](https://github.com/nf-core/tools/issues/1509))
- Fix bug in pipeline readme logo URL
- Set the default DAG graphic output to HTML to have a default that does not depend on Graphviz being installed on the host system ([#1512](https://github.com/nf-core/tools/pull/1512)).
- Removed retry strategy for AWS tests CI, as Nextflow now handles spot instance retries itself
- Add `.prettierignore` file to stop Prettier linting tests from running over test files
- Made module template test command match the default used in `nf-core modules create-test-yml` ([#1562](https://github.com/nf-core/tools/issues/1562))
- Removed black background from Readme badges now that GitHub has a dark mode, added Tower launch badge.
- Don't save md5sum for `versions.yml` when running `nf-core modules create-test-yml` ([#1511](https://github.com/nf-core/tools/pull/1511))

### General

- Add actions workflow to respond to `@nf-core-bot fix linting` comments on nf-core/tools PRs
- Use [`$XDG_CONFIG_HOME`](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) or `~/.config/nf-core` instead of `~/.nfcore` for API cache (the latter can be safely deleted)
- Consolidate GitHub API calls into a shared function that uses authentication from the [`gh` GitHub cli tool](https://cli.github.com/) or `GITHUB_AUTH_TOKEN` to avoid rate limiting ([#1499](https://github.com/nf-core/tools/pull/1499))
- Add an empty line to `modules.json`, `params.json` and `nextflow-schema.json` when dumping them to avoid prettier errors.
- Remove empty JSON schema definition groups to avoid usage errors ([#1419](https://github.com/nf-core/tools/issues/1419))
- Bumped the minimum version of `rich` from `v10` to `v10.7.0`

### Modules

- Add a new command `nf-core modules mulled` which can generate the name for a multi-tool container image.
- Add a new command `nf-core modules test` which runs pytests locally.
- Print include statement to terminal when `modules install` ([#1520](https://github.com/nf-core/tools/pull/1520))
- Allow follow links when generating `test.yml` file with `nf-core modules create-test-yml` ([1570](https://github.com/nf-core/tools/pull/1570))
- Escaped test run output before logging it, to avoid a rich `MarkupError`

### Linting

- Don't allow a `.nf-core.yaml` file, should be `.yml` ([#1515](https://github.com/nf-core/tools/pull/1515)).
- `shell` blocks now recognised to avoid error `when: condition has too many lines` ([#1557](https://github.com/nf-core/tools/issues/1557))
- Fixed error when using comments after `input` tuple lines ([#1542](https://github.com/nf-core/tools/issues/1542))
- Don't lint the `shell` block when `script` is used ([1558](https://github.com/nf-core/tools/pull/1558))
- Check that `template` is used in `script` blocks
- Tweaks to CLI output display of lint results

## [v2.3.2 - Mercury Vulture Fixed Formatting](https://github.com/nf-core/tools/releases/tag/2.3.2) - [2022-03-24]

Very minor patch release to fix the full size AWS tests and re-run the template sync, which partially failed due to GitHub pull-requests being down at the time of release.

### Template

- Updated the AWS GitHub actions to let nf-core/tower-action use it's defaults for pipeline and git sha ([#1488](https://github.com/nf-core/tools/pull/1488))
- Add prettier editor extension to `gitpod.yml` in template ([#1485](https://github.com/nf-core/tools/pull/1485))
- Remove traces of markdownlint in the template ([#1486](https://github.com/nf-core/tools/pull/1486)
- Remove accidentally added line in `CHANGELOG.md` in the template ([#1487](https://github.com/nf-core/tools/pull/1487))
- Update linting to check that `.editorconfig` is there and `.yamllint.yml` isn't.

## [v2.3.1 - Mercury Vulture Formatting](https://github.com/nf-core/tools/releases/tag/2.3.1) - [2022-03-23]

This patch release is primarily to address problems that we had in the v2.3 release with code linting.
Instead of resolving those specific issues, we chose to replace the linting tools (`markdownlint`, `yamllint`) with a new tool: [_Prettier_](https://prettier.io)

This is a fairly major change and affects a lot of files. However, it will hopefully simplify future usage.
Prettier can auto-format many different file formats (for pipelines the most relevant are markdown and YAML) and is extensible with plugins ([Nextflow](https://github.com/nf-core/prettier-plugin-nextflow), anyone?).
It tends to be a bit less strict than `markdownlint` and `yamllint` and importantly _can fix files for you_ rather than just complaining.

The sync PR may be a little big because of many major changes (whitespace, quotation mark styles etc).
To help with the merge, _**we highly recommend running Prettier on your pipeline's codebase before attempting the template merge**_.
If you take this approach, please copy `.editorconfig` and `.prettierrc.yml` from the template to your pipeline root first,
as they configure the behaviour of Prettier.

To run Prettier, go to the base of the repository where `.editorconfig` and `.prettierrc.yml` are located.
Make sure your `git status` is clean so that the changes don't affect anything you're working on and run:

```bash
prettier --write .
```

This runs Prettier and tells it to fix any issues it finds in place.

Please note that there are many excellent integrations for Prettier available, for example VSCode can be set up to automatically format files on save.

### Template

- Replace `markdownlint` and `yamllint` with [_Prettier_](https://prettier.io) for linting formatting / whitespace ([#1470](https://github.com/nf-core/tools/pull/1470))
- Add CI test using `editorconfig-checker` for other file types to look for standardised indentation and formatting ([#1476](https://github.com/nf-core/tools/pull/1476))
- Add md5sum check of `versions.yml` to `test.yml` on the modules template.
- Update bundled module wrappers to latest versions ([#1462](https://github.com/nf-core/tools/pull/1462))
- Renamed `assets/multiqc_config.yaml` to `assets/multiqc_config.yml` (`yml` not `yaml`) ([#1471](https://github.com/nf-core/tools/pull/1471))

### General

- Convert nf-core/tools API / lint test documentation to MyST ([#1245](https://github.com/nf-core/tools/pull/1245))
- Build documentation for the `nf-core modules lint` tests ([#1250](https://github.com/nf-core/tools/pull/1250))
- Fix some colours in the nf-core/tools API docs ([#1467](https://github.com/nf-core/tools/pull/1467))
- Install tools inside GitPod Docker using the repo itself and not from Conda.
- Rewrite GitHub Actions workflow for publishing the GitPod Docker image.
- Improve config for PyTest so that you can run `pytest` instead of `pytest tests/` ([#1461](https://github.com/nf-core/tools/pull/1461))
- New pipeline lint test `multiqc_config` that checks YAML structure instead of basic file contents ([#1461](https://github.com/nf-core/tools/pull/1461))
- Updates to the GitPod docker image to install the latest version of nf-core/tools

## [v2.3 - Mercury Vulture](https://github.com/nf-core/tools/releases/tag/2.3) - [2022-03-15]

### Template

- Removed mention of `--singularity_pull_docker_container` in pipeline `README.md`
- Replaced equals with ~ in nf-core headers, to stop false positive unresolved conflict errors when committing with VSCode.
- Add retry strategy for AWS megatests after releasing [nf-core/tower-action v2.2](https://github.com/nf-core/tower-action/releases/tag/v2.2)
- Added `.nf-core.yml` file with `repository_type: pipeline` for modules commands
- Update igenomes path to the `BWAIndex` to fetch the whole `version0.6.0` folder instead of only the `genome.fa` file
- Remove pinned Node version in the GitHub Actions workflows, to fix errors with `markdownlint`
- Bumped `nf-core/tower-action` to `v3` and removed `pipeline` and `revision` from the AWS workflows, which were not needed
- Add yamllint GitHub Action.
- Add `.yamllint.yml` to avoid line length and document start errors ([#1407](https://github.com/nf-core/tools/issues/1407))
- Add `--publish_dir_mode` back into the pipeline template ([nf-core/rnaseq#752](https://github.com/nf-core/rnaseq/issues/752#issuecomment-1039451607))
- Add optional loading of of pipeline-specific institutional configs to `nextflow.config`
- Make `--outdir` a mandatory parameter ([nf-core/tools#1415](https://github.com/nf-core/tools/issues/1415))
- Add pipeline description and authors between triple quotes to avoid errors with apostrophes ([#2066](https://github.com/nf-core/tools/pull/2066), [#2104](https://github.com/nf-core/tools/pull/2104))

### General

- Updated `nf-core download` to work with latest DSL2 syntax for containers ([#1379](https://github.com/nf-core/tools/issues/1379))
- Made `nf-core modules create` detect repository type with explicit `.nf-core.yml` instead of random readme stuff ([#1391](https://github.com/nf-core/tools/pull/1391))
- Added a Gitpod environment and Dockerfile ([#1384](https://github.com/nf-core/tools/pull/1384))
  - Adds conda, Nextflow, nf-core, pytest-workflow, mamba, and pip to base Gitpod Docker image.
  - Adds GH action to build and push Gitpod Docker image.
  - Adds Gitpod environment to template.
  - Adds Gitpod environment to tools with auto build of nf-core tool.
- Shiny new command-line help formatting ([#1403](https://github.com/nf-core/tools/pull/1403))
- Call the command line help with `-h` as well as `--help` (was formerly just the latter) ([#1404](https://github.com/nf-core/tools/pull/1404))
- Add `.yamllint.yml` config file to avoid line length and document start errors in the tools repo itself.
- Switch to `yamllint-github-action`to be able to configure yaml lint exceptions ([#1404](https://github.com/nf-core/tools/issues/1413))
- Prevent module linting KeyError edge case ([#1321](https://github.com/nf-core/tools/issues/1321))
- Bump-versions: Don't trim the trailing newline on files, causes editorconfig linting to fail ([#1265](https://github.com/nf-core/tools/issues/1265))
- Handle exception in `nf-core list` when a broken git repo is found ([#1273](https://github.com/nf-core/tools/issues/1273))
- Updated URL for pipeline lint test docs ([#1348](https://github.com/nf-core/tools/issues/1348))
- Updated `nf-core create` to tolerate failures and retry when fetching pipeline logos from the website ([#1369](https://github.com/nf-core/tools/issues/1369))
- Modified the CSS overriding `sphinx_rtd_theme` default colors to fix some glitches in the API documentation ([#1294](https://github.com/nf-core/tools/issues/1294))

### Modules

- New command `nf-core modules info` that prints nice documentation about a module to the terminal :sparkles: ([#1427](https://github.com/nf-core/tools/issues/1427))
- Linting a pipeline now fails instead of warning if a local copy of a module does not match the remote ([#1313](https://github.com/nf-core/tools/issues/1313))
- Fixed linting bugs where warning was incorrectly generated for:
  - `Module does not emit software version`
  - `Container versions do not match`
  - `input:` / `output:` not being specified in module
  - Allow for containers from other biocontainers resource as defined [here](https://github.com/nf-core/modules/blob/cde237e7cec07798e5754b72aeca44efe89fc6db/modules/cat/fastq/main.nf#L7-L8)
- Fixed traceback when using `stageAs` syntax as defined [here](https://github.com/nf-core/modules/blob/cde237e7cec07798e5754b72aeca44efe89fc6db/modules/cat/fastq/main.nf#L11)
- Added `nf-core schema docs` command to output pipline parameter documentation in Markdown format for inclusion in GitHub and other documentation systems ([#741](https://github.com/nf-core/tools/issues/741))
- Allow conditional process execution from the configuration file ([#1393](https://github.com/nf-core/tools/pull/1393))
- Add linting for when condition([#1397](https://github.com/nf-core/tools/pull/1397))
- Added modules ignored table to `nf-core modules bump-versions`. ([#1234](https://github.com/nf-core/tools/issues/1234))
- Added `--conda-package-version` flag for specifying version of conda package in `nf-core modules create`. ([#1238](https://github.com/nf-core/tools/issues/1238))
- Add option of writing diffs to file in `nf-core modules update` using either interactive prompts or the new `--diff-file` flag.
- Fixed edge case where module names that were substrings of other modules caused both to be installed ([#1380](https://github.com/nf-core/tools/issues/1380))
- Tweak handling of empty files when generating the test YAML ([#1376](https://github.com/nf-core/tools/issues/1376))
  - Fail linting if a md5sum for an empty file is found (instead of a warning)
  - Don't skip the md5 when generating a test file if an empty file is found (so that linting fails and can be manually checked)
- Linting checks test files for `TODO` statements as well as the main module code ([#1271](https://github.com/nf-core/tools/issues/1271))
- Handle error if `manifest` isn't set in `nextflow.config` ([#1418](https://github.com/nf-core/tools/issues/1418))

## [v2.2 - Lead Liger](https://github.com/nf-core/tools/releases/tag/2.2) - [2021-12-14]

### Template

- Update repo logos to utilize [GitHub's `#gh-light/dark-mode-only`](https://docs.github.com/en/github/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#specifying-the-theme-an-image-is-shown-to), to switch between logos optimized for light or dark themes. The old repo logos have to be removed (in `docs/images` and `assets/`).
- Deal with authentication with private repositories
- Bump minimun Nextflow version to 21.10.3
- Convert pipeline template to updated Nextflow DSL2 syntax
- Solve circular import when importing `nf_core.modules.lint`
- Disable cache in `nf_core.utils.fetch_wf_config` while performing `test_wf_use_local_configs`.
- Modify software version channel handling to support multiple software version emissions (e.g. from mulled containers), and multiple software versions.
- Update `dumpsoftwareversion` module to correctly report versions with trailing zeros.
- Remove `params.hostnames` from the pipeline template ([#1304](https://github.com/nf-core/tools/issues/1304))
- Update `.gitattributes` to mark installed modules and subworkflows as `linguist-generated` ([#1311](https://github.com/nf-core/tools/issues/1311))
- Adding support for [Julia](https://julialang.org) package environments to `nextflow.config`([#1317](https://github.com/nf-core/tools/pull/1317))
- New YAML issue templates for pipeline bug reports and feature requests, with a much richer interface ([#1165](https://github.com/nf-core/tools/pull/1165))
- Update AWS test GitHub Actions to use v2 of [nf-core/tower-action](https://github.com/nf-core/tower-action)
- Post linting comment even when `linting.yml` fails
- Update `CONTRIBUTION.md` bullets to remove points related to `scrape_software_versions.py`
- Update AWS test to set Nextflow version to 21.10.3

### General

- Made lint check for parameters defaults stricter [[#992](https://github.com/nf-core/tools/issues/992)]
  - Default values in `nextflow.config` must match the defaults given in the schema (anything with `{` in, or in `main.nf` is ignored)
  - Defaults in `nextflow.config` must now match the variable _type_ specified in the schema
  - If you want the parameter to not have a default value, use `null`
  - Strings set to `false` or an empty string in `nextflow.config` will now fail linting
- Bump minimun Nextflow version to 21.10.3
- Changed `questionary` `ask()` to `unsafe_ask()` to not catch `KeyboardInterupts` ([#1237](https://github.com/nf-core/tools/issues/1237))
- Fixed bug in `nf-core launch` due to revisions specified with `-r` not being added to nextflow command. ([#1246](https://github.com/nf-core/tools/issues/1246))
- Update regex in `readme` test of `nf-core lint` to agree with the pipeline template ([#1260](https://github.com/nf-core/tools/issues/1260))
- Update 'fix' message in `nf-core lint` to conform to the current command line options. ([#1259](https://github.com/nf-core/tools/issues/1259))
- Fixed bug in `nf-core list` when `NXF_HOME` is set
- Run CI test used to create and lint/run the pipeline template with minimum and latest edge release of NF ([#1304](https://github.com/nf-core/tools/issues/1304))
- New YAML issue templates for tools bug reports and feature requests, with a much richer interface ([#1165](https://github.com/nf-core/tools/pull/1165))
- Handle synax errors in Nextflow config nicely when running `nf-core schema build` ([#1267](https://github.com/nf-core/tools/pull/1267))
- Erase temporary files and folders while performing Python tests (pytest)
- Remove base `Dockerfile` used for DSL1 pipeline container builds
- Run tests with Python 3.10
- [#1363](https://github.com/nf-core/tools/pull/1363) Fix tools CI workflow nextflow versions.

### Modules

- Fixed typo in `modules_utils.py`.
- Fixed failing lint test when process section was missing from module. Also added the local failing tests to the warned section of the output table. ([#1235](https://github.com/nf-core/tools/issues/1235))
- Added `--diff` flag to `nf-core modules update` which shows the diff between the installed files and the versions
- Update `nf-core modules create` help texts which were not changed with the introduction of the `--dir` flag
- Check if README is from modules repo
- Update module template to DSL2 v2.0 (remove `functions.nf` from modules template and updating `main.nf` ([#1289](https://github.com/nf-core/tools/pull/))
- Substitute get process/module name custom functions in module `main.nf` using template replacement ([#1284](https://github.com/nf-core/tools/issues/1284))
- Check test YML file for md5sums corresponding to empty files ([#1302](https://github.com/nf-core/tools/issues/1302))
- Exit with an error if empty files are found when generating the test YAML file ([#1302](https://github.com/nf-core/tools/issues/1302))

## [v2.1 - Zinc Zebra](https://github.com/nf-core/tools/releases/tag/2.1) - [2021-07-27]

### Template

- Correct regex pattern for file names in `nextflow_schema.json`
- Remove `.` from nf-core/tools command examples
- Update Nextflow installation link in pipeline template ([#1201](https://github.com/nf-core/tools/issues/1201))
- Command `hostname` is not portable [[#1212](https://github.com/nf-core/tools/pull/1212)]
- Changed how singularity and docker links are written in template to avoid duplicate links

### General

- Changed names of some flags with `-r` as short options to make the flags more consistent between commands.

### Modules

- Added consistency checks between installed modules and `modules.json` ([#1199](https://github.com/nf-core/tools/issues/1199))
- Added support excluding or specifying version of modules in `.nf-core.yml` when updating with `nf-core modules install --all` ([#1204](https://github.com/nf-core/tools/issues/1204))
- Created `nf-core modules update` and removed updating options from `nf-core modules install`
- Added missing function call to `nf-core lint` ([#1198](https://github.com/nf-core/tools/issues/1198))
- Fix `nf-core lint` not filtering modules test when run with `--key` ([#1203](https://github.com/nf-core/tools/issues/1203))
- Fixed `nf-core modules install` not working when installing from branch with `-b` ([#1218](https://github.com/nf-core/tools/issues/1218))
- Added prompt to choose between updating all modules or named module in `nf-core modules update`
- Check if modules is installed before trying to update in `nf-core modules update`
- Verify that a commit SHA provided with `--sha` exists for `install/update` commands
- Add new-line to `main.nf` after `bump-versions` command to make ECLint happy

## [v2.0.1 - Palladium Platypus Junior](https://github.com/nf-core/tools/releases/tag/2.0.1) - [2021-07-13]

### Template

- Critical tweak to add `--dir` declaration to `nf-core lint` GitHub Actions `linting.yml` workflow

### General

- Add `--dir` declaration to `nf-core sync` GitHub Actions `sync.yml` workflow

## [v2.0 - Palladium Platypus](https://github.com/nf-core/tools/releases/tag/2.0) - [2021-07-13]

### :warning: Major enhancements & breaking changes

This marks the first Nextflow DSL2-centric release of `tools` which means that some commands won't work in full with DSL1 pipelines anymore. Please use a `v1.x` version of `tools` for such pipelines or better yet join us to improve our DSL2 efforts! Here are the most important changes:

- The pipeline template has been completely re-written in DSL2
- A module template has been added to auto-create best-practice DSL2 modules to speed up development
- A whole suite of commands have been added to streamline the creation, installation, removal, linting and version bumping of DSL2 modules either installed within pipelines or the nf-core/modules repo

### Template

- Move TODO item of `contains:` map in a YAML string [[#1082](https://github.com/nf-core/tools/issues/1082)]
- Trigger AWS tests via Tower API [[#1160](https://github.com/nf-core/tools/pull/1160)]

### General

- Fixed a bug in the Docker image build for tools that failed due to an extra hyphen. [[#1069](https://github.com/nf-core/tools/pull/1069)]
- Regular release sync fix - this time it was to do with JSON serialisation [[#1072](https://github.com/nf-core/tools/pull/1072)]
- Fixed bug in schema validation that ignores upper/lower-case typos in parameters [[#1087](https://github.com/nf-core/tools/issues/1087)]
- Bugfix: Download should use path relative to workflow for configs
- Remove lint checks for files related to conda and docker as not needed anymore for DSL2
- Removed `params_used` lint check because of incompatibility with DSL2
- Added`modules bump-versions` command to `README.md`
- Update docs for v2.0 release

### Modules

- Update comment style of modules `functions.nf` template file [[#1076](https://github.com/nf-core/tools/issues/1076)]
- Changed working directory to temporary directory for `nf-core modules create-test-yml` [[#908](https://github.com/nf-core/tools/issues/908)]
- Use Biocontainers API instead of quayi.io API for `nf-core modules create` [[#875](https://github.com/nf-core/tools/issues/875)]
- Update `nf-core modules install` to handle different versions of modules [#1116](https://github.com/nf-core/tools/pull/1116)
- Added `nf-core modules bump-versions` command to update all versions in the `nf-core/modules` repository [[#1123](https://github.com/nf-core/tools/issues/1123)]
- Updated `nf-core modules lint` to check whether a `git_sha` exists in the `modules.json` file or whether a new version is available [[#1114](https://github.com/nf-core/tools/issues/1114)]
- Refactored `nf-core modules` command into one file per command [#1124](https://github.com/nf-core/tools/pull/1124)
- Updated `nf-core modules remove` to also remove entry in `modules.json` file ([#1115](https://github.com/nf-core/tools/issues/1115))
- Bugfix: Interactive prompt for `nf-core modules install` was receiving too few arguments
- Added progress bar to creation of 'modules.json'
- Updated `nf-core modules list` to show versions of local modules
- Improved exit behavior by replacing `sys.exit` with exceptions
- Updated `nf-core modules remove` to remove module entry in `modules.json` if module directory is missing
- Create extra tempdir as work directory for `nf-core modules create-test-yml` to avoid adding the temporary files to the `test.yml`
- Refactored passing of command line arguments to `nf-core` commands and subcommands ([#1139](https://github.com/nf-core/tools/issues/1139), [#1140](https://github.com/nf-core/tools/issues/1140))
- Check for `modules.json` for entries of modules that are not actually installed in the pipeline [[#1141](https://github.com/nf-core/tools/issues/1141)]
- Added `<keywords>` argument to `nf-core modules list` for filtering the listed modules. ([#1139](https://github.com/nf-core/tools/issues/1139)
- Added support for a `bump-versions` configuration file [[#1142](https://github.com/nf-core/tools/issues/1142)]
- Fixed `nf-core modules create-test-yml` so it doesn't break when the output directory is supplied [[#1148](https://github.com/nf-core/tools/issues/1148)]
- Updated `nf-core modules lint` to work with new directory structure [[#1159](https://github.com/nf-core/tools/issues/1159)]
- Updated `nf-core modules install` and `modules.json` to work with new directory structure ([#1159](https://github.com/nf-core/tools/issues/1159))
- Updated `nf-core modules remove` to work with new directory structure [[#1159](https://github.com/nf-core/tools/issues/1159)]
- Restructured code and removed old table style in `nf-core modules list`
- Fixed bug causing `modules.json` creation to loop indefinitly
- Added `--all` flag to `nf-core modules install`
- Added `remote` and `local` subcommands to `nf-core modules list`
- Fix bug due to restructuring in modules template
- Added checks for verifying that the remote repository is well formed
- Added checks to `ModulesCommand` for verifying validity of remote repositories
- Misc. changes to `modules install`: check that module exist in remote, `--all` is has `--latest` by default.

#### Sync

- Don't set the default value to `"null"` when a parameter is initialised as `null` in the config [[#1074](https://github.com/nf-core/tools/pull/1074)]

#### Tests

- Added a test for the `version_consistency` lint check
- Refactored modules tests into separate files, and removed direct comparisons with number of tests in `lint` tests ([#1158](https://github.com/nf-core/tools/issues/1158))

## [v1.14 - Brass Chicken :chicken:](https://github.com/nf-core/tools/releases/tag/1.14) - [2021-05-11]

### Template

- Add the implicit workflow declaration to `main.nf` DSL2 template [[#1056](https://github.com/nf-core/tools/issues/1056)]
- Fixed an issue regarding explicit disabling of unused container engines [[#972](https://github.com/nf-core/tools/pull/972)]
- Removed trailing slash from `params.igenomes_base` to yield valid s3 paths (previous paths work with Nextflow but not aws cli)
- Added a timestamp to the trace + timetime + report + dag filenames to fix overwrite issue on AWS
- Rewrite the `params_summary_log()` function to properly ignore unset params and have nicer formatting [[#971](https://github.com/nf-core/tools/issues/971)]
- Fix overly strict `--max_time` formatting regex in template schema [[#973](https://github.com/nf-core/tools/issues/973)]
- Convert `d` to `day` in the `cleanParameters` function to make Duration objects like `2d` pass the validation [[#858](https://github.com/nf-core/tools/issues/858)]
- Added nextflow version to quick start section and adjusted `nf-core bump-version` [[#1032](https://github.com/nf-core/tools/issues/1032)]
- Use latest stable Nextflow version `21.04.0` for CI tests instead of the `-edge` release

### Download

- Fix bug in `nf-core download` where image names were getting a hyphen in `nf-core` which was breaking things.
- Extensive new interactive prompts for all command line flags [[#1027](https://github.com/nf-core/tools/issues/1027)]
  - It is now recommended to run `nf-core download` without any cli options and follow prompts (though flags can be used to run non-interactively if you wish)
- New helper code to set `$NXF_SINGULARITY_CACHEDIR` and add to `.bashrc` if desired [[#1027](https://github.com/nf-core/tools/issues/1027)]

### Launch

- Strip values from `nf-core launch` web response which are `False` and have no default in the schema [[#976](https://github.com/nf-core/tools/issues/976)]
- Improve API caching code when polling the website, fixes noisy log message when waiting for a response [[#1029](https://github.com/nf-core/tools/issues/1029)]
- New interactive prompts for pipeline name [[#1027](https://github.com/nf-core/tools/issues/1027)]

### Modules

- Added `tool_name_underscore` to the module template to allow TOOL_SUBTOOL in `main.nf` [[#1011](https://github.com/nf-core/tools/issues/1011)]
- Added `--conda-name` flag to `nf-core modules create` command to allow sidestepping questionary [[#988](https://github.com/nf-core/tools/issues/988)]
- Extended `nf-core modules lint` functionality to check tags in `test.yml` and to look for a entry in the `pytest_software.yml` file
- Update `modules` commands to use new test tag format `tool/subtool`
- New modules lint test comparing the `functions.nf` file to the template version
- Modules installed from alternative sources are put in folders based on the name of the source repository

### Linting

- Fix bug in nf-core lint config skipping for the `nextflow_config` test [[#1019](https://github.com/nf-core/tools/issues/1019)]
- New `-k`/`--key` cli option for `nf-core lint` to allow you to run only named lint tests, for faster local debugging
- Merge markers lint test - ignore binary files, allow config to ignore specific files [[#1040](https://github.com/nf-core/tools/pull/1040)]
- New lint test to check if all defined pipeline parameters are mentioned in `main.nf` [[#1038](https://github.com/nf-core/tools/issues/1038)]
- Added fix to remove warnings about params that get converted from camelCase to camel-case [[#1035](https://github.com/nf-core/tools/issues/1035)]
- Added pipeline schema lint checks for missing parameter description and parameters outside of groups [[#1017](https://github.com/nf-core/tools/issues/1017)]

### General

- Try to fix the fix for the automated sync when we submit too many PRs at once [[#970](https://github.com/nf-core/tools/issues/970)]
- Rewrite how the tools documentation is deployed to the website, to allow multiple versions
- Created new Docker image for the tools cli package - see installation docs for details [[#917](https://github.com/nf-core/tools/issues/917)]
- Ignore permission errors for setting up requests cache directories to allow starting with an invalid or read-only `HOME` directory

## [v1.13.3 - Copper Crocodile Resurrection :crocodile:](https://github.com/nf-core/tools/releases/tag/1.13.2) - [2021-03-24]

- Running tests twice with `nf-core modules create-test-yml` to catch unreproducible md5 sums [[#890](https://github.com/nf-core/tools/issues/890)]
- Fix sync error again where the Nextflow edge release needs to be used for some pipelines
- Fix bug with `nf-core lint --release` (`NameError: name 'os' is not defined`)
- Added linebreak to linting comment so that markdown header renders on PR comment properly
- `nf-core modules create` command - if no bioconda package is found, prompt user for a different bioconda package name
- Updated module template `main.nf` with new test data paths

## [v1.13.2 - Copper Crocodile CPR :crocodile: :face_with_head_bandage:](https://github.com/nf-core/tools/releases/tag/1.13.2) - [2021-03-23]

- Make module template pass the EC linter [[#953](https://github.com/nf-core/tools/pull/953)]
- Added better logging message if a user doesn't specificy the directory correctly with `nf-core modules` commands [[#942](https://github.com/nf-core/tools/pull/942)]
- Fixed parameter validation bug caused by JSONObject [[#937](https://github.com/nf-core/tools/issues/937)]
- Fixed template creation error regarding file permissions [[#932](https://github.com/nf-core/tools/issues/932)]
- Split the `create-lint-wf` tests up into separate steps in GitHub Actions to make the CI results easier to read
- Added automated PR comments to the Markdown, YAML and Python lint CI tests to explain failures (tools and pipeline template)
- Make `nf-core lint` summary table borders coloured according to overall pass / fail status
- Attempted a fix for the automated sync when we submit too many PRs at once [[#911](https://github.com/nf-core/tools/issues/911)]

## [v1.13.1 - Copper Crocodile Patch :crocodile: :pirate_flag:](https://github.com/nf-core/tools/releases/tag/1.13.1) - [2021-03-19]

- Fixed bug in pipeline linting markdown output that gets posted to PR comments [[#914]](https://github.com/nf-core/tools/issues/914)
- Made text for the PR branch CI check less verbose with a TLDR in bold at the top
- A number of minor tweaks to the new `nf-core modules lint` code

## [v1.13 - Copper Crocodile](https://github.com/nf-core/tools/releases/tag/1.13) - [2021-03-18]

### Template

- **Major new feature** - Validation of pipeline parameters [[#426]](https://github.com/nf-core/tools/issues/426)
  - The addition runs as soon as the pipeline launches and checks the pipeline input parameters two main things:
    - No parameters are supplied that share a name with core Nextflow options (eg. `--resume` instead of `-resume`)
    - Supplied parameters validate against the pipeline JSON schema (eg. correct variable types, required values)
  - If either parameter validation fails or the pipeline has errors, a warning is given about any unexpected parameters found which are not described in the pipeline schema.
  - This behaviour can be disabled by using `--validate_params false`
- Added profiles to support the [Charliecloud](https://hpc.github.io/charliecloud/) and [Shifter](https://nersc.gitlab.io/development/shifter/how-to-use/) container engines [[#824](https://github.com/nf-core/tools/issues/824)]
  - Note that Charliecloud requires Nextflow version `v21.03.0-edge` or later.
- Profiles for container engines now explicitly _disable_ all other engines [[#867](https://github.com/nf-core/tools/issues/867)]
- Fixed typo in nf-core-lint CI that prevented the markdown summary from being automatically posted on PRs as a comment.
- Changed default for `--input` from `data/*{1,2}.fastq.gz` to `null`, as this is now validated by the schema as a required value.
- Removed support for `--name` parameter for custom run names.
  - The same functionality for MultiQC still exists with the core Nextflow `-name` option.
- Added to template docs about how to identify process name for resource customisation
- The parameters `--max_memory` and `--max_time` are now validated against a regular expression [[#793](https://github.com/nf-core/tools/issues/793)]
  - Must be written in the format `123.GB` / `456.h` with any of the prefixes listed in the [Nextflow docs](https://www.nextflow.io/docs/latest/process.html#memory)
  - Bare numbers no longer allowed, avoiding people from trying to specify GB and actually specifying bytes.
- Switched from cookiecutter to Jinja2 [[#880]](https://github.com/nf-core/tools/pull/880)
- Finally dropped the wonderful [cookiecutter](https://github.com/cookiecutter/cookiecutter) library that was behind the first pipeline template that led to nf-core [[#880](https://github.com/nf-core/tools/pull/880)]
  - Now rendering templates directly using [Jinja](https://jinja.palletsprojects.com/), which is what cookiecutter was doing anyway

### Modules

Initial addition of a number of new helper commands for working with DSL2 modules:

- `modules list` - List available modules
- `modules install` - Install a module from nf-core/modules
- `modules remove` - Remove a module from a pipeline
- `modules create` - Create a module from the template
- `modules create-test-yml` - Create the `test.yml` file for a module with md5 sums, tags, commands and names added
- `modules lint` - Check a module against nf-core guidelines

You can read more about each of these commands in the main tools documentation (see `README.md` or <https://nf-co.re/tools>)

### Tools helper code

- Fixed some bugs in the command line interface for `nf-core launch` and improved formatting [[#829](https://github.com/nf-core/tools/pull/829)]
- New functionality for `nf-core download` to make it compatible with DSL2 pipelines [[#832](https://github.com/nf-core/tools/pull/832)]
  - Singularity images in module files are now discovered and fetched
  - Direct downloads of Singularity images in python allowed (much faster than running `singularity pull`)
  - Downloads now work with `$NXF_SINGULARITY_CACHEDIR` so that pipelines sharing containers have efficient downloads
- Changed behaviour of `nf-core sync` command [[#787](https://github.com/nf-core/tools/issues/787)]
  - Instead of opening or updating a PR from `TEMPLATE` directly to `dev`, a new branch is now created from `TEMPLATE` and a PR opened from this to `dev`.
  - This is to make it easier to fix merge conflicts without accidentally bringing the entire pipeline history back into the `TEMPLATE` branch (which makes subsequent sync merges much more difficult)

### Linting

- Major refactor and rewrite of pipieline linting code
  - Much better code organisation and maintainability
  - New automatically generated documentation using Sphinx
  - Numerous new tests and functions, removal of some unnecessary tests
- Added lint check for merge markers [[#321]](https://github.com/nf-core/tools/issues/321)
- Added new option `--fix` to automatically correct some problems detected by linting
- Added validation of default params to `nf-core schema lint` [[#823](https://github.com/nf-core/tools/issues/823)]
- Added schema validation of GitHub action workflows to lint function [[#795](https://github.com/nf-core/tools/issues/795)]
- Fixed bug in schema title and description validation
- Added second progress bar for conda dependencies lint check, as it can be slow [[#299](https://github.com/nf-core/tools/issues/299)]
- Added new lint test to check files that should be unchanged from the pipeline.
- Added the possibility to ignore lint tests using a `nf-core-lint.yml` config file [[#809](https://github.com/nf-core/tools/pull/809)]

## [v1.12.1 - Silver Dolphin](https://github.com/nf-core/tools/releases/tag/1.12.1) - [2020-12-03]

### Template

- Finished switch from `$baseDir` to `$projectDir` in `iGenomes.conf` and `main.nf`
  - Main fix is for `smail_fields` which was a bug introduced in the previous release. Sorry about that!
- Ported a number of small content tweaks from nf-core/eager to the template [[#786](https://github.com/nf-core/tools/issues/786)]
  - Better contributing documentation, more placeholders in documentation files, more relaxed markdownlint exceptions for certain HTML tags, more content for the PR and issue templates.

### Tools helper code

- Pipeline schema: make parameters of type `range` to `number`. [[#738](https://github.com/nf-core/tools/issues/738)]
- Respect `$NXF_HOME` when looking for pipelines with `nf-core list` [[#798](https://github.com/nf-core/tools/issues/798)]
- Swapped PyInquirer with questionary for command line questions in `launch.py` [[#726](https://github.com/nf-core/tools/issues/726)]
  - This should fix conda installation issues that some people had been hitting
  - The change also allows other improvements to the UI
- Fix linting crash when a file deleted but not yet staged in git [[#796](https://github.com/nf-core/tools/issues/796)]

## [v1.12 - Mercury Weasel](https://github.com/nf-core/tools/releases/tag/1.12) - [2020-11-19]

### Tools helper code

- Updated `nf_core` documentation generator for building [https://nf-co.re/tools-docs/](https://nf-co.re/tools-docs/)

### Template

- Make CI comments work with PRs from forks [[#765](https://github.com/nf-core/tools/issues/765)]
  - Branch protection and linting results should now show on all PRs
- Updated GitHub issue templates, which had stopped working
- Refactored GitHub Actions so that the AWS full-scale tests are triggered after docker build is finished
  - DockerHub push workflow split into two - one for dev, one for releases
- Updated actions to no longer use `set-env` which is now depreciating [[#739](https://github.com/nf-core/tools/issues/739)]
- Added config import for `test_full` in `nextflow.config`
- Switched depreciated `$baseDir` to `$projectDir`
- Updated minimum Nextflow version to `20.04.10`
- Make Nextflow installation less verbose in GitHub Actions [[#780](https://github.com/nf-core/tools/pull/780)]

### Linting

- Updated code to display colours in GitHub Actions log output
- Allow tests to pass with `dev` version of nf-core/tools (previous failure due to base image version)
- Lint code no longer tries to post GitHub PR comments. This is now done in a GitHub Action only.

## [v1.11 - Iron Tiger](https://github.com/nf-core/tools/releases/tag/1.11) - [2020-10-27]

### Template

- Fix command error in `awstest.yml` GitHub Action workflow.
- Allow manual triggering of AWS test GitHub Action workflows.
- Remove TODO item, which was proposing the usage of additional files beside `usage.md` and `output.md` for documentation.
- Added a Podman profile, which enables Podman as container.
- Updated linting for GitHub actions AWS tests workflows.

### Linting

- Made a base-level `Dockerfile` a warning instead of failure
- Added a lint failure if the old `bin/markdown_to_html.r` script is found
- Update `rich` package dependency and use new markup escaping to change `[[!]]` back to `[!]` again

### Other

- Pipeline sync - fetch full repo when checking out before sync
- Sync - Add GitHub actions manual trigger option

## [v1.10.2 - Copper Camel _(brought back from the dead)_](https://github.com/nf-core/tools/releases/tag/1.10.2) - [2020-07-31]

Second patch release to address some small errors discovered in the pipeline template.
Apologies for the inconvenience.

- Fix syntax error in `/push_dockerhub.yml` GitHub Action workflow
- Change `params.readPaths` -> `params.input_paths` in `test_full.config`
- Check results when posting the lint results as a GitHub comment
  - This feature is unfortunately not possible when making PRs from forks outside of the nf-core organisation for now.
- More major refactoring of the automated pipeline sync
  - New GitHub Actions matrix parallelisation of sync jobs across pipelines [[#673](https://github.com/nf-core/tools/issues/673)]
  - Removed the `--all` behaviour from `nf-core sync` as we no longer need it
  - Sync now uses a new list of pipelines on the website which does not include archived pipelines [[#712](https://github.com/nf-core/tools/issues/712)]
  - When making a PR it checks if a PR already exists - if so it updates it [[#710](https://github.com/nf-core/tools/issues/710)]
  - More tests and code refactoring for more stable code. Hopefully fixes 404 error [[#711](https://github.com/nf-core/tools/issues/711)]

## [v1.10.1 - Copper Camel _(patch)_](https://github.com/nf-core/tools/releases/tag/1.10.1) - [2020-07-30]

Patch release to fix the automatic template synchronisation, which failed in the v1.10 release.

- Improved logging: `nf-core --log-file log.txt` now saves a verbose log to disk.
- nf-core/tools GitHub Actions pipeline sync now uploads verbose log as an artifact.
- Sync - fixed several minor bugs, made logging less verbose.
- Python Rich library updated to `>=4.2.1`
- Hopefully fix git config for pipeline sync so that commit comes from @nf-core-bot
- Fix sync auto-PR text indentation so that it doesn't all show as code
- Added explicit flag `--show-passed` for `nf-core lint` instead of taking logging verbosity

## [v1.10 - Copper Camel](https://github.com/nf-core/tools/releases/tag/1.10) - [2020-07-30]

### Pipeline schema

This release of nf-core/tools introduces a major change / new feature: pipeline schema.
These are [JSON Schema](https://json-schema.org/) files that describe all of the parameters for a given
pipeline with their ID, a description, a longer help text, an optional default value, a variable _type_
(eg. `string` or `boolean`) and more.

The files will be used in a number of places:

- Automatic validation of supplied parameters when running pipelines
  - Pipeline execution can be immediately stopped if a required `param` is missing,
    or does not conform to the patterns / allowed values in the schema.
- Generation of pipeline command-line help
  - Running `nextflow run <pipeline> --help` will use the schema to generate a help text automatically
- Building online documentation on the [nf-core website](https://nf-co.re)
- Integration with 3rd party graphical user interfaces

To support these new schema files, nf-core/tools now comes with a new set of commands: `nf-core schema`.

- Pipeline schema can be generated or updated using `nf-core schema build` - this takes the parameters from
  the pipeline config file and prompts the developer for any mismatch between schema and pipeline.
  - Once a skeleton Schema file has been built, the command makes use of a new nf-core website tool to provide
    a user friendly graphical interface for developers to add content to their schema: [https://nf-co.re/pipeline_schema_builder](https://nf-co.re/pipeline_schema_builder)
- Pipelines will be automatically tested for valid schema that describe all pipeline parameters using the
  `nf-core schema lint` command (also included as part of the main `nf-core lint` command).
- Users can validate their set of pipeline inputs using the `nf-core schema validate` command.

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

- Add `--publish_dir_mode` parameter [#585](https://github.com/nf-core/tools/issues/585)
- Isolate R library paths to those in container [#541](https://github.com/nf-core/tools/issues/541)
- Added new style of pipeline parameters JSON schema to pipeline template
- Add ability to attach MultiQC reports to completion emails when using `mail`
- Update `output.md` and add in 'Pipeline information' section describing standard NF and pipeline reporting.
- Build Docker image using GitHub Actions, then push to Docker Hub (instead of building on Docker Hub)
- Add Slack channel badge in pipeline README
- Allow multiple container tags in `ci.yml` if performing multiple tests in parallel
- Add AWS CI tests and full tests GitHub Actions workflows
- Update AWS CI tests and full tests secrets names
- Added `macs_gsize` for danRer10, based on [this post](https://biostar.galaxyproject.org/p/18272/)
- Add information about config files used for workflow execution (`workflow.configFiles`) to summary
- Fix `markdown_to_html.py` to work with Python 2 and 3.
- Change `params.reads` -> `params.input`
- Adding TODOs and MultiQC process in DSL2 template
- Change `params.readPaths` -> `params.input_paths`
- Added a `.github/.dockstore.yml` config file for automatic workflow registration with [dockstore.org](https://dockstore.org/)

### Linting

- Refactored PR branch tests to be a little clearer.
- Linting error docs explain how to add an additional branch protecton rule to the `branch.yml` GitHub Actions workflow.
- Adapted linting docs to the new PR branch tests.
- Failure for missing the readme bioconda badge is now a warn, in case this badge is not relevant
- Added test for template `{{ cookiecutter.var }}` placeholders
- Fix failure when providing version along with build id for Conda packages
- New `--json` and `--markdown` options to print lint results to JSON / markdown files
- Linting code now automatically posts warning / failing results to GitHub PRs as a comment if it can
- Added AWS GitHub Actions workflows linting
- Fail if `params.input` isn't defined.
- Beautiful new progress bar to look at whilst linting is running and awesome new formatted output on the command line :heart_eyes:
  - All made using the excellent [`rich` python library](https://github.com/willmcgugan/rich) - check it out!
- Tests looking for `TODO` strings should now ignore editor backup files. [#477](https://github.com/nf-core/tools/issues/477)

### nf-core/tools Continuous Integration

- Added CI test to check for PRs against `master` in tools repo
- CI PR branch tests fixed & now automatically add a comment on the PR if failing, explaining what is wrong
- Move some of the issue and PR templates into HTML `<!-- comments -->` so that they don't show in issues / PRs

### Other

- Describe alternative installation method via conda with `conda env create`
- nf-core/tools version number now printed underneath header artwork
- Bumped Conda version shipped with nfcore/base to 4.8.2
- Added log message when creating new pipelines that people should talk to the community about their plans
- Fixed 'on completion' emails sent using the `mail` command not containing body text.
- Improved command-line help text for nf-core/tools
- `nf-core list` now hides archived pipelines unless `--show_archived` flag is set
- Command line tools now checks if there is a new version of nf-core/tools available
  - Disable this by setting the environment variable `NFCORE_NO_VERSION_CHECK`, eg. `export NFCORE_NO_VERSION_CHECK=1`
- Better command-line output formatting of nearly all `nf-core` commands using [`rich`](https://github.com/willmcgugan/rich)

## [v1.9 - Platinum Pigeon](https://github.com/nf-core/tools/releases/tag/1.9) - [2020-02-20]

### Continuous integration

- Travis CI tests are now deprecated in favor of GitHub Actions within the pipeline template.
  - `nf-core bump-version` support has been removed for `.travis.yml`
  - `nf-core lint` now fails if a `.travis.yml` file is found
- Ported nf-core/tools Travis CI automation to GitHub Actions.
- Fixed the build for the nf-core/tools API documentation on the website

### Template

- Rewrote the documentation markdown > HTML conversion in Python instead of R
- Fixed rendering of images in output documentation [#391](https://github.com/nf-core/tools/issues/391)
- Removed the requirement for R in the conda environment
- Make `params.multiqc_config` give an _additional_ MultiQC config file instead of replacing the one that ships with the pipeline
- Ignore only `tests/` and `testing/` directories in `.gitignore` to avoid ignoring `test.config` configuration file
- Rephrase docs to promote usage of containers over Conda to ensure reproducibility
- Stage the workflow summary YAML file within MultiQC work directory

### Linting

- Removed linting for CircleCI
- Allow any one of `params.reads` or `params.input` or `params.design` before warning
- Added whitespace padding to lint error URLs
- Improved documentation for lint errors
- Allow either `>=` or `!>=` in nextflow version checks (the latter exits with an error instead of just warning) [#506](https://github.com/nf-core/tools/issues/506)
- Check that `manifest.version` ends in `dev` and throw a warning if not
  - If running with `--release` check the opposite and fail if not
- Tidied up error messages and syntax for linting GitHub actions branch tests
- Add YAML validator
- Don't print test results if we have a critical error

### Other

- Fix automatic synchronisation of the template after releases of nf-core/tools
- Improve documentation for installing `nf-core/tools`
- Replace preprint by the new nf-core publication in Nature Biotechnology :champagne:
- Use `stderr` instead of `stdout` for header artwork
- Tolerate unexpected output from `nextflow config` command
- Add social preview image
- Added a [release checklist](.github/RELEASE_CHECKLIST.md) for the tools repo

## [v1.8 - Black Sheep](https://github.com/nf-core/tools/releases/tag/1.8) - [2020-01-27]

### Continuous integration

- GitHub Actions CI workflows are now included in the template pipeline
  - Please update these files to match the existing tests that you have in `.travis.yml`
- Travis CI tests will be deprecated from the next `tools` release
- Linting will generate a warning if GitHub Actions workflows do not exist and if applicable to remove Travis CI workflow file i.e. `.travis.yml`.

### Tools helper code

- Refactored the template synchronisation code to be part of the main nf-core tool
- `nf-core bump-version` now also bumps the version string of the exported conda environment in the Dockerfile
- Updated Blacklist of synced pipelines
- Ignore pre-releases in `nf-core list`
- Updated documentation for `nf-core download`
- Fixed typo in `nf-core launch` final command
- Handle missing pipeline descriptions in `nf-core list`
- Migrate tools package CI to GitHub Actions

### Linting

- Adjusted linting to enable `patch` branches from being tested
- Warn if GitHub Actions workflows do not exist, warn if `.travis.yml` and circleCI are there
- Lint for `Singularity` file and raise error if found [#458](https://github.com/nf-core/tools/issues/458)
- Added linting of GitHub Actions workflows `linting.yml`, `ci.yml` and `branch.yml`
- Warn if pipeline name contains upper case letters or non alphabetical characters [#85](https://github.com/nf-core/tools/issues/85)
- Make CI tests of lint code pass for releases

### Template pipeline

- Fixed incorrect paths in iGenomes config as described in issue [#418](https://github.com/nf-core/tools/issues/418)
- Fixed incorrect usage of non-existent parameter in the template [#446](https://github.com/nf-core/tools/issues/446)
- Add UCSC genomes to `igenomes.config` and add paths to all genome indices
- Change `maxMultiqcEmailFileSize` parameter to `max_multiqc_email_size`
- Export conda environment in Docker file [#349](https://github.com/nf-core/tools/issues/349)
- Change remaining parameters from `camelCase` to `snake_case` [#39](https://github.com/nf-core/hic/issues/39)
  - `--singleEnd` to `--single_end`
  - `--igenomesIgnore` to `--igenomes_ignore`
  - Having the old camelCase versions of these will now throw an error
- Add `autoMounts=true` to default singularity profile
- Add in `markdownlint` checks that were being ignored by default
- Disable ansi logging in the travis CI tests
- Move `params`section from `base.config` to `nextflow.config`
- Use `env` scope to export `PYTHONNOUSERSITE` in `nextflow.config` to prevent conflicts with host Python environment
- Bump minimum Nextflow version to `19.10.0` - required to properly use `env` scope in `nextflow.config`
- Added support for nf-tower in the travis tests, using public mailbox nf-core@mailinator.com
- Add link to [Keep a Changelog](http://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](http://semver.org/spec/v2.0.0.html) to CHANGELOG
- Adjusted `.travis.yml` checks to allow for `patch` branches to be tested
- Add Python 3.7 dependency to the `environment.yml` file
- Remove `awsbatch` profile cf [nf-core/configs#71](https://github.com/nf-core/configs/pull/71)
- Make `scrape_software_versions.py` compatible with Python3 to enable miniconda3 in [base image PR](https://github.com/nf-core/tools/pull/462)
- Add GitHub Actions workflows and respective linting
- Add `NXF_ANSI_LOG` as global environment variable to template GitHub Actions CI workflow
- Fixed global environment variable in GitHub Actions CI workflow
- Add `--awscli` parameter
- Add `README.txt` path for genomes in `igenomes.config` [nf-core/atacseq#75](https://github.com/nf-core/atacseq/issues/75)
- Fix buggy ANSI codes in pipeline summary log messages
- Add a `TODO` line in the new GitHub Actions CI test files

### Base Docker image

- Use miniconda3 instead of miniconda for a Python 3k base environment
  - If you still need Python 2 for your pipeline, add `conda-forge::python=2.7.4` to the dependencies in your `environment.yml`
- Update conda version to 4.7.12

### Other

- Updated Base Dockerfile to Conda 4.7.10
- Entirely switched from Travis-Ci.org to Travis-Ci.com for template and tools
- Improved core documentation (`-profile`)

## [v1.7 - Titanium Kangaroo](https://github.com/nf-core/tools/releases/tag/1.7) - [2019-10-07]

### Tools helper code

- The tools `create` command now sets up a `TEMPLATE` and a `dev` branch for syncing
- Fixed issue [379](https://github.com/nf-core/tools/issues/379)
- nf-core launch now uses stable parameter schema version 0.1.0
- Check that PR from patch or dev branch is acceptable by linting
- Made code compatible with Python 3.7
- The `download` command now also fetches institutional configs from nf-core/configs
- When listing pipelines, a nicer message is given for the rare case of a detached `HEAD` ref in a locally pulled pipeline. [#297](https://github.com/nf-core/tools/issues/297)
- The `download` command can now compress files into a single archive.
- `nf-core create` now fetches a logo for the pipeline from the nf-core website
- The readme should now be rendered properly on PyPI.

### Syncing

- Can now sync a targeted pipeline via command-line
- Updated Blacklist of synced pipelines
- Removed `chipseq` from Blacklist of synced pipelines
- Fixed issue [#314](https://github.com/nf-core/tools/issues/314)

### Linting

- If the container slug does not contain the nf-core organisation (for example during development on a fork), linting will raise a warning, and an error with release mode on

### Template pipeline

- Add new code for Travis CI to allow PRs from patch branches too
- Fix small typo in central readme of tools for future releases
- Small code polishing + typo fix in the template main.nf file
- Header ANSI codes no longer print `[2m` to console when using `-with-ansi`
- Switched to yaml.safe_load() to fix PyYAML warning that was thrown because of a possible [exploit](<https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation>)
- Add `nf-core` citation
- Add proper `nf-core` logo for tools
- Add `Quick Start` section to main README of template
- Fix [Docker RunOptions](https://github.com/nf-core/tools/pull/351) to get UID and GID set in the template
- `Dockerfile` now specifically uses the proper release tag of the nfcore/base image
- Use [`file`](https://github.com/nf-core/tools/pull/354) instead of `new File`
  to avoid weird behavior such as making an `s3:/` directory locally when using
  an AWS S3 bucket as the `--outdir`.
- Fix workflow.onComplete() message when finishing pipeline
- Update URL for joining the nf-core slack to [https://nf-co.re/join/slack](https://nf-co.re/join/slack)
- Add GitHub Action for CI and Linting
- [Increased default time limit](https://github.com/nf-core/tools/issues/370) to 4h
- Add direct link to the pipeline slack channel in the contribution guidelines
- Add contributions and support heading with links to contribution guidelines and link to the pipeline slack channel in the main README
- Fix Parameters JSON due to new versionized structure
- Added conda-forge::r-markdown=1.1 and conda-forge::r-base=3.6.1 to environment
- Plain-text email template now has nf-core ASCII artwork
- Template configured to use logo fetched from website
- New option `--email_on_fail` which only sends emails if the workflow is not successful
- Add file existence check when checking software versions
- Fixed issue [#165](https://github.com/nf-core/tools/issues/165) - Use `checkIfExists`
- Consistent spacing for `if` statements
- Add sensible resource labels to `base.config`

### Other

- Bump `conda` to 4.6.14 in base nf-core Dockerfile
- Added a Code of Conduct to nf-core/tools, as only the template had this before
- TravisCI tests will now also start for PRs from `patch` branches, [to allow fixing critical issues](https://github.com/nf-core/tools/pull/392) without making a new major release

## [v1.6 - Brass Walrus](https://github.com/nf-core/tools/releases/tag/1.6) - [2020-04-09]

### Syncing

- Code refactoring to make the script more readable
- No travis build failure anymore on sync errors
- More verbose logging

### Template pipeline

- awsbatch `work-dir` checking moved to nextflow itself. Removed unsatisfiable check in main.nf template.
- Fixed markdown linting
- Tools CI testing now runs markdown lint on compiled template pipeline
- Migrated large portions of documentation to the [nf-core website](https://github.com/nf-core/nf-co.re/pull/93)
- Removed Gitter references in `.github/` directories for `tools/` and pipeline template.
- Changed `scrape_software_versions.py` to output `.csv` file
- Added `export_plots` parameter to multiqc config
- Corrected some typos as listed [here](https://github.com/nf-core/tools/issues/348) to Guidelines

### Tools helper code

- Drop [nf-core/rnaseq](https://github.com/nf-core/rnaseq]) from `blacklist.json` to make template sync available
- Updated main help command to sort the subcommands in a more logical order
- Updated readme to describe the new `nf-core launch` command
- Fix bugs in `nf-core download`
  - The _latest_ release is now fetched by default if not specified
  - Downloaded pipeline files are now properly executable.
- Fixed bugs in `nf-core list`
  - Sorting now works again
  - Output is partially coloured (better highlighting out of date pipelines)
  - Improved documentation
- Fixed bugs in `nf-core lint`
  - The order of conda channels is now correct, avoiding occasional erroneous errors that packages weren't found ([#207](https://github.com/nf-core/tools/issues/207))
  - Allow edge versions in nf-core pipelines
- Add reporting of ignored errored process
  - As a solution for [#103](https://github.com/nf-core/tools/issues/103))
- Add Bowtie2 and BWA in iGenome config file template

## [v1.5 - Iron Shark](https://github.com/nf-core/tools/releases/tag/1.5) - [2019-03-13]

### Template pipeline

- Dropped Singularity file
- Summary now logs details of the cluster profile used if from [nf-core/configs](https://github.com/nf-core/configs)
- Dockerhub is used in favor of Singularity Hub for pulling when using the Singularity profile
- Changed default container tag from latest to dev
- Brought the logo to life
- Change the default filenames for the pipeline trace files
- Remote fetch of nf-core/configs profiles fails gracefully if offline
- Remove `params.container` and just directly define `process.container` now
- Completion email now includes MultiQC report if not too big
- `params.genome` is now checked if set, to ensure that it's a valid iGenomes key
- Together with nf-core/configs, helper function now checks hostname and suggests a valid config profile
- `awsbatch` executor requires the `tracedir` not to be set to an `s3` bucket.

### Tools helper code

- New `nf-core launch` command to interactively launch nf-core pipelines from command-line
  - Works with a `parameters.settings.json` file shipped with each pipeline
  - Discovers additional `params` from the pipeline dynamically
- Drop Python 3.4 support
- `nf-core list` now only shows a value for _"is local latest version"_ column if there is a local copy.
- Lint markdown formatting in automated tests
  - Added `markdownlint-cli` for checking Markdown syntax in pipelines and tools repo
- Syncing now reads from a `blacklist.json` in order to exclude pipelines from being synced if necessary.
- Added nf-core tools API description to assist developers with the classes and functions available.
  - Docs are automatically built by Travis CI and updated on the nf-co.re website.
- Introduced test for filtering remote workflows by keyword.
- Build tools python API docs

  - Use Travis job for api doc generation and publish

- `nf-core bump-version` now stops before making changes if the linting fails
- Code test coverage
  - Introduced test for filtering remote workflows by keyword
- Linting updates
  - Now properly searches for conda packages in default channels
  - Now correctly validates version pinning for packages from PyPI
  - Updates for changes to `process.container` definition

### Other

- Bump `conda` to 4.6.7 in base nf-core Dockerfile

## [v1.4 - Tantalum Butterfly](https://github.com/nf-core/tools/releases/tag/1.4) - [2018-12-12]

### Template pipeline

- Institutional custom config profiles moved to github `nf-core/configs`
  - These will now be maintained centrally as opposed to being shipped with the pipelines in `conf/`
  - Load `base.config` by default for all profiles
  - Removed profiles named `standard` and `none`
  - Added parameter `--igenomesIgnore` so `igenomes.config` is not loaded if parameter clashes are observed
  - Added parameter `--custom_config_version` for custom config version control. Can use this parameter to provide commit id for reproducibility. Defaults to `master`
  - Deleted custom configs from template in `conf/` directory i.e. `uzh.config`, `binac.config` and `cfc.config`
- `multiqc_config` and `output_md` are now put into channels instead of using the files directly (see issue [#222](https://github.com/nf-core/tools/issues/222))
- Added `local.md` to cookiecutter template in `docs/configuration/`. This was referenced in `README.md` but not present.
- Major overhaul of docs to add/remove parameters, unify linking of files and added description for providing custom configs where necessary
- Travis: Pull the `dev` tagged docker image for testing
- Removed UPPMAX-specific documentation from the template.

### Tools helper code

- Make Travis CI tests fail on pull requests if the `CHANGELOG.md` file hasn't been updated
- Minor bugfixing in Python code (eg. removing unused import statements)
- Made the web requests caching work on multi-user installations
- Handle exception if nextflow isn't installed
- Linting: Update for Travis: Pull the `dev` tagged docker image for testing

## [v1.3 - Citreous Swordfish](https://github.com/nf-core/tools/releases/tag/1.3) - [2018-11-21]

- `nf-core create` command line interface updated
  - Interactive prompts for required arguments if not given
  - New flag for workflow author
- Updated channel order for bioconda/conda-forge channels in environment.yaml
- Increased code coverage for sub command `create` and `licenses`
- Fixed nasty dependency hell issue between `pytest` and `py` package in Python 3.4.x
- Introduced `.coveragerc` for pytest-cov configuration, which excludes the pipeline template now from being reported
- Fix [189](https://github.com/nf-core/tools/issues/189): Check for given conda and PyPi package dependencies, if their versions exist
- Added profiles for `cfc`,`binac`, `uzh` that can be synced across pipelines
  - Ordering alphabetically for profiles now
- Added `pip install --upgrade pip` to `.travis.yml` to update pip in the Travis CI environment

## [v1.2](https://github.com/nf-core/tools/releases/tag/1.2) - [2018-10-01]

- Updated the `nf-core release` command
  - Now called `nf-core bump-versions` instead
  - New flag `--nextflow` to change the required nextflow version instead
- Template updates
  - Simpler installation of the `nf-core` helper tool, now directly from PyPI
  - Bump minimum nextflow version to `0.32.0` - required for built in `manifest.nextflowVersion` check and access to `workflow.manifest` variables from within nextflow scripts
  - New `withName` syntax for configs
  - Travis tests fail if PRs come against the `master` branch, slightly refactored
  - Improved GitHub contributing instructions and pull request / issue templates
- New lint tests
  - `.travis.yml` test for PRs made against the `master` branch
  - Automatic `--release` option not used if the travis repo is `nf-core/tools`
  - Warnings if depreciated variables `params.version` and `params.nf_required_version` are found
- New `nf-core licences` subcommand to show licence for each conda package in a workflow
- `nf-core list` now has options for sorting pipeline nicely
- Latest version of conda used in nf-core base docker image
- Updated PyPI deployment to correctly parse the markdown readme (hopefully!)
- New GitHub contributing instructions and pull request template

## [v1.1](https://github.com/nf-core/tools/releases/tag/1.1) - [2018-08-14]

Very large release containing lots of work from the first nf-core hackathon, held in SciLifeLab Stockholm.

- The [Cookiecutter template](https://github.com/nf-core/cookiecutter) has been merged into tools
  - The old repo above has been archived
  - New pipelines are now created using the command `nf-core create`
  - The nf-core template and associated linting are now controlled under the same version system
- Large number of template updates and associated linting changes
  - New simplified cookiecutter variable usage
  - Refactored documentation - simplified and reduced duplication
  - Better `manifest` variables instead of `params` for pipeline name and version
  - New integrated nextflow version checking
  - Updated travis docker pull command to use tagging to allow release tests to pass
  - Reverted Docker and Singularity syntax to use `ENV` hack again
- Improved Python readme parsing for PyPI
- Updated Travis tests to check that the correct `dev` branch is being targeted
- New sync tool to automate pipeline updates
  - Once initial merges are complete, a nf-core bot account will create PRs for future template updates

## [v1.0.1](https://github.com/nf-core/tools/releases/tag/1.0.1) - [2018-07-18]

The version 1.0 of nf-core tools cannot be installed from PyPi. This patch fixes it, by getting rid of the requirements.txt plus declaring the dependent modules in the setup.py directly.

## [v1.0](https://github.com/nf-core/tools/releases/tag/1.0) - [2018-06-12]

Initial release of the nf-core helper tools package. Currently includes four subcommands:

- `nf-core list`: List nf-core pipelines with local info
- `nf-core download`: Download a pipeline and singularity container
- `nf-core lint`: Check pipeline against nf-core guidelines
- `nf-core release`: Update nf-core pipeline version number
