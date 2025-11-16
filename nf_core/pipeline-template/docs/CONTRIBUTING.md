---
title: Contributing
markdownPlugin: checklist
---

# `{{ name }}`: Contributing Guidelines

Hi there!
Many thanks for taking an interest in improving {{ name }}.

This page describes the recommended nf-core way for contributing to both {{ name }} and nf-core pipelines in general.

- [General contribution guidelines](#general-contribution-guidelines): for common procedures or guides across all nf-core pipelines.
- [Pipeline specific contribution guidelines](#pipeline-specific-contribution-guidelines): for any procedures or guides specific to the development conventions of {{ name }}.

{% if is_nfcore -%}

> [!NOTE]
> If you need help using or modifying {{ name }} then the best place to ask is on the nf-core Slack [#{{ short_name }}](https://nfcore.slack.com/channels/{{ short_name }}) channel ([join our Slack here](https://nf-co.re/join/slack)).

{% endif -%}

## General contribution guidelines

### Contribution quick start

If you'd like to write some code for {{ name }}, the standard workflow is as follows:

- [ ] Make sure you have Nextflow, nf-core tools, and nf-test installed - see the [nf-core/tools repository](https://github.com/nf-core/tools).
- [ ] Check that there isn't already an issue about your idea in the [{{ name }} issues](https://github.com/{{ name }}/issues) to avoid duplicating work. If there isn't one already, please create one so that others know you're working on this.
- [ ] [Fork](https://help.github.com/en/github/getting-started-with-github/fork-a-repo) the [{{ name }} repository](https://github.com/{{ name }}) to your GitHub account.
- [ ] Make the necessary changes / additions within your forked repository following [Pipeline conventions](#pipeline-contribution-conventions), ideally on a branch
- [ ] - If you are fixing a major bug, please using a branch nmmed `patch` and see the [Patch](#patch) section below.
- [ ] Update any relevant documentation within the `docs/` folder and use nf-core/tools to update `nextflow_schema.json` using nf-core/tools.
- [ ] [Lint](#lint-tests) your code using nf-core/tools
- [ ] Run and/or update tests as appropriate (see [Tests](#tests) section below).
- [ ] Submit a Pull Request against the `dev` branch and request for the code to be reviewed and merged.

If you're not used to this workflow with git, you can start with some [docs from GitHub](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests) or even their [excellent `git` resources](https://try.github.io/).

{% if is_nfcore -%}

### Getting help

For further information/help, please consult the [{{ name }} documentation](https://nf-co.re/{{ short_name }}/usage) and don't hesitate to get in touch on the nf-core Slack [#{{ short_name }}](https://nfcore.slack.com/channels/{{ short_name }}) channel ([join our Slack here](https://nf-co.re/join/slack)).

{% endif -%}

{%- if codespaces %}

### GitHub Codespaces

This repo includes a devcontainer configuration which will create a GitHub Codespaces for Nextflow development! This is an online developer environment that runs in your browser, complete with VSCode and a terminal.

To get started:

- Open the repo in [Codespaces](https://github.com/{{ name }}/codespaces)
- Tools installed
  - nf-core
  - Nextflow

Devcontainer specs:

- [DevContainer config](.devcontainer/devcontainer.json)
  {%- endif %}

### Tests

{% if test_config -%}
You have the option to test your changes locally by running the pipeline using nf-test.
We recommend to use the `--verbose` flag to see the Nextflow console log output in addition to nf-test's own output.

```bash
nf-test test --tag test --profile +docker --verbose
```

{% endif -%}

When you create a pull request with changes, [GitHub Actions](https://github.com/features/actions) will run automatic tests.
Typically, pull-requests are only fully reviewed when these tests are passing, though of course we can help out before then.

{% if test_config %}There are typically two types of tests that run:{% endif %}

#### Lint tests

`nf-core` has a [set of guidelines](https://nf-co.re/docs/contributing/guidelines) which all pipelines must adhere to.
To enforce these and ensure that all pipelines stay in sync, you can use the nf-core/tools package to run the linting locally with the command.

```bash
nf-core pipelines lint <pipeline-directory>
```

If any failures or warnings are encountered, please follow the listed URL for more documentation.
The full list of tests can be seen [here](https://nf-co.re/docs/nf-core-tools/api_reference/latest/pipeline_lint_tests/actions_awsfulltest).

{%- if test_config %}

#### Pipeline tests

Each `nf-core` pipeline should be set up with a minimal set of test-data.
`GitHub Actions` then runs the pipeline on this data to ensure that it exits successfully.
If there are any failures then the automated tests fail.
These tests are run both with the latest available version of `Nextflow` and also the minimum required version that is stated in the pipeline code.
{%- endif %}

### Patch

:warning: Only in the unlikely and regretful event of a release happening with a bug.

- [ ] On your own fork, make a new branch `patch` based on `upstream/main` or `upstream/master`.
- [ ] Fix the bug, and use nf-core tools to bump version to the next semantic version e.g., `1.2.3` -> `1.2.4`.
- [ ] Open a pull-request from `patch` directly to `main`/`master` with the changes.

### Pipeline contribution conventions

To make the `{{ name }}` code and processing logic more understandable for new contributors and to ensure quality, we semi-standardise the way the code and other contributions are written.

#### Adding a new step

If you wish to contribute a new step to the pipeline, please use the following general nf-core coding procedure.
Please also refer to the [pipeline-specific contribution guidelines](#pipeline-specific-contribution-guidelines):

- [ ] Define the corresponding [input channel](#channel-naming-schemes) into your new process from the expected previous process channel.
- [ ] Install a module using nf-core tools, or write a local module (check [info about resources](#default-processes-resource-requirements)), and add it to the target `<workflow>.nf`.
- [ ] Define the output channel if needed (see below), mixing both the version output channel into `ch_versions` and relevant files into `ch_multiqc`.
- [ ] Add any new/update parameters to `nextflow.config` with a [default](#default-values) (see below).
- [ ] Add any new/update parameters to `nextflow_schema.json` with help text using [nf-core/tools](#default-values).
- [ ] Add validation for all relevant parameters to the pipeline`utilisation section of`utils*nfcore*{{ shortname }}\_pipeline/main.nf` subworkflow.
- [ ] Perform local tests to validate that the new code works as expected.
- [ ] If applicable, add a new test in the `tests` directory.
- [ ] Update `usage.md`, `output.md`, `citation.md` docs as appropriate.
- [ ] [Lint](lint) the code using nf-core/tools
- [ ] Update any diagrams or pipeline images as necessary
      {%- if multiqc %}
- [ ]. Update MultiQC config `assets/multiqc_config.yml` so relevant suffixes, file name clean up and module plots are in the appropriate order. - [ ] applicable, add a [MultiQC](https://seqera.io/multiqc/) module.
- [ ]. Add a description of the output files and if relevant any appropriate images from the MultiQC report to `docs/output.md`.
  {%- endif %}

If you need to update the minimum required Nextflow version, please see the [Nextflow version bumping](#nextflow-version-bumping) section below.

#### Channel naming schemes

Please use the following naming schemes for channels, to make it easy to understand what is going where.

- initial process channel: `ch_output_from_<process>`
- intermediate and terminal channels: `ch_<previousprocess>_for_<nextprocess>`

#### Default values

Parameters should be initialised / defined with default values within the `params` scope in `nextflow.config`.

Once there, use:

```bash
nf-core pipelines schema build
```

To update `nextflow_schema.json`.

#### Default processes resource requirements

If writing a local module, you should specify a default set of resource requirements for the process.

Sensible defaults for process resource requirements (CPUs / memory / time) for a process should be defined in `conf/base.config`.
These should generally be specified with generic `withLabel:` selectors, so they can be shared across multiple processes/steps of the pipeline.

nf-core provides a set of standard labels that should be followed where possible, and can be seen in the [nf-core pipeline template](https://github.com/nf-core/tools/blob/main/nf_core/pipeline-template/conf/base.config).
These labels have resource defaults for a single core-process, a module requiring use of a GPU, and then different levels of multi-core configurations for increasingly large memory requirements defined with standardised labels.

The process resources should be passed on to the tool dynamically within the process using the `${task.cpus}` Nextflow variable, and where necessary the `${task.memory}` variable, in the command of the `script:` block (see example [here](https://github.com/nf-core/modules/blob/bd1b6a40f55933d94b8c9ca94ec8c1ea0eaf4b82/modules/nf-core/samtools/bam2fq/main.nf#L30)).

#### Images and figures

For overview images and other documents we follow the nf-core [style guidelines and examples](https://nf-co.re/docs/guidelines/graphic_design/overview).

#### Nextflow version bumping

If you are using a new feature from core Nextflow, you may bump the minimum required version of nextflow in the pipeline with:

```bash
nf-core pipelines bump-version --nextflow . [min-nf-version]
```

## Pipeline specific contribution guidelines

<!-- TODO nf-core: Add any pipeline specific contribution guidelines here, such as coding styles, procedures, checklists etc. -->
