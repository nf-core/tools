---
title: Linting a pipeline
description: Guarantee that your pipeline meets nf-core community guidelines.
weight: 70
section: pipelines
---

The `lint` subcommand checks a given pipeline for all nf-core community guidelines.
This is the same test that is used on the automated continuous integration tests.

For example, the current version looks something like this:

<!-- RICH-CODEX
timeout: 60
working_dir: tmp/nf-core-nextbigthing
before_command: >
  echo "lint: { pipeline_todos: false }" >> .nf-core.yml
fake_command: nf-core lint
-->

![`nf-core lint`](../images/nf-core-lint.svg)

You can use the `-k` / `--key` flag to run only named tests for faster debugging, eg: `nf-core lint -k files_exist -k files_unchanged`. The `nf-core lint` command lints the current working directory by default, to specify another directory you can use `--dir <directory>`.

### Linting documentation

Each test result name on the left is a terminal hyperlink.
In most terminals you can <kbd>ctrl</kbd> + <kbd>click</kbd> ( <kbd>cmd</kbd> + <kbd>click</kbd>) these
links to open documentation specific to this test in your browser.

Alternatively visit <https://nf-co.re/tools-docs/lint_tests/index.html> and find your test to read more.

### Linting config

It's sometimes desirable to disable certain lint tests, especially if you're using nf-core/tools with your
own pipeline that is outside of nf-core.

To help with this, you can add a tools config file to your pipeline called `.nf-core.yml` in the pipeline root directory (previously: `.nf-core-lint.yml`).
Here you can list the names of any tests that you would like to disable and set them to `False`, for example:

```yaml
lint:
  actions_awsfulltest: False
  pipeline_todos: False
```

Some lint tests allow greater granularity, for example skipping a test only for a specific file.
This is documented in the test-specific docs but generally involves passing a list, for example:

```yaml
lint:
  files_exist:
    - CODE_OF_CONDUCT.md
  files_unchanged:
    - assets/email_template.html
    - CODE_OF_CONDUCT.md
```

Note that you have to list all configurations for the `nf-core lint` command under the `lint:` field in the `.nf-core.yml` file, as this file is also used for configuration of other commands.

### Automatically fix errors

Some lint tests can try to automatically fix any issues they find. To enable this functionality, use the `--fix` flag.
The pipeline must be a `git` repository with no uncommitted changes for this to work.
This is so that any automated changes can then be reviewed and undone (`git checkout .`) if you disagree.

### Lint results output

The output from `nf-core lint` is designed to be viewed on the command line and is deliberately succinct.
You can view all passed tests with `--show-passed` or generate JSON / markdown results with the `--json` and `--markdown` flags.
