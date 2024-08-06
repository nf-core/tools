# nf-core/tools: Contributing Guidelines

Hi there! Many thanks for taking an interest in improving nf-core/tools.

If you need help then the best place to ask is the [`#tools` channel](https://nfcore.slack.com/channels/tools) on the nf-core Slack.
You can get an invite on the [nf-core website](https://nf-co.re/join/slack/).

## Contribution workflow

If you'd like to write some code for nf-core/tools, the standard workflow
is as follows:

1. Check that there isn't [already an issue](https://github.com/nf-core/tools/issues) about your idea to avoid duplicating work.
   - If there isn't one already, please create one so that others know you're working on this
2. Fork the [nf-core/tools repository](https://github.com/nf-core/tools) to your GitHub account
3. Make the necessary changes / additions within your forked repository
4. Submit a Pull Request against the `dev` branch and wait for the code to be reviewed and merged.

If you're not used to this workflow with git, you can start with some [basic docs from GitHub](https://help.github.com/articles/fork-a-repo/).

## Installing dev requirements

If you want to work with developing the nf-core/tools code, you'll need a couple of extra Python packages.
These are listed in `requirements-dev.txt` and can be installed as follows:

```bash
pip install --upgrade -r requirements-dev.txt
```

Then install your local fork of nf-core/tools:

```bash
pip install -e .
```

## Code formatting

### Ruff

All Python code in nf-core/tools must be passed through the [Ruff code linter and formatter](https://github.com/astral-sh/ruff).
This ensures a harmonised code formatting style throughout the package, from all contributors.

You can run Ruff on the command line (it's included in `requirements-dev.txt`) - eg. to run recursively on the whole repository:

```bash
ruff format .
```

Alternatively, Ruff has [integrations for most common editors](https://github.com/astral-sh/ruff-lsp) and VSCode(https://github.com/astral-sh/ruff-vscode)
to automatically format code when you hit save.

There is an automated CI check that runs when you open a pull-request to nf-core/tools that will fail if
any code does not adhere to Ruff formatting.

Ruff has been adopted for linting and formatting in replacement of Black, isort (for imports) and pyupgrade. It also includes Flake8.

### pre-commit hooks

This repository comes with [pre-commit](https://pre-commit.com/) hooks for ruff and Prettier. pre-commit automatically runs checks before a commit is committed into the git history. If all checks pass, the commit is made, if files are changed by the pre-commit hooks, the user is informed and has to stage the changes and attempt the commit again.

You can use the pre-commit hooks if you like, but you don't have to. The CI on Github will run the same checks as the tools installed with pre-commit. If the pre-commit checks pass, then the same checks in the CI will pass, too.

You can install the pre-commit hooks into the development environment by running the following command in the root directory of the repository.

```bash
pre-commit install --install-hooks
```

You can also run all pre-commit hooks without making a commit:

```bash
pre-commit run --all
```

## API Documentation

We aim to write function docstrings according to the [Google Python style-guide](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings). These are used to automatically generate package documentation on the nf-core website using Sphinx.
You can find this documentation here: [https://nf-co.re/tools/docs/](https://nf-co.re/tools/docs/)

If you would like to test the documentation, you can install Sphinx locally by following Sphinx's [installation instruction](https://www.sphinx-doc.org/en/master/usage/installation.html).
Once done, you can run `make clean` and then `make html` in the `docs/api` directory of `nf-core tools`.
The HTML will then be generated in `docs/api/_build/html`.

## Tests

When you create a pull request with changes, [GitHub Actions](https://github.com/features/actions) will run automatic tests.
Typically, pull-requests are only fully reviewed when these tests are passing, though of course we can help out before then.

There are two types of tests that run:

### Unit Tests

The nf-core tools package has a set of unit tests bundled, which can be found in the `tests/` directory.
New features should also come with new tests, to keep the test-coverage high (we use [codecov.io](https://codecov.io/gh/nf-core/tools/) to check this automatically).

You can try running the tests locally before pushing code using the following command:

```bash
pytest --color=yes
```

### Lint Tests

nf-core/tools contains both the main nf-core template for pipelines and the code used to test that pipelines adhere to the nf-core guidelines.
As these two commonly need to be edited together, we test the creation of a pipeline and then linting using a CI check.
This ensures that any changes we make to either the linting or the template stay in sync.
You can replicate this process locally with the following commands:

```bash
nf-core pipelines create -n testpipeline -d "This pipeline is for testing"
nf-core pipelines lint nf-core-testpipeline
```

## GitHub Codespaces

This repo includes a devcontainer configuration which will create a GitHub Codespaces for Nextflow development! This is an online developer environment that runs in your browser, complete with VSCode and a terminal.

To get started:

- Open the repo in [Codespaces](https://github.com/nf-core/tools/codespaces)
- Tools installed
  - nf-core
  - Nextflow

Devcontainer specs:

- [DevContainer config](.devcontainer/devcontainer.json)

## nf-core-bot

nf-core has a bot which you can use to perform certain actions on a PR.

- Fix linting:

If the linting tests is failing on a PR to nf-core/tools, you can post a comment with the magic words:

```
@nf-core-bot fix linting
```

The bot will try to fix the linting, push to your branch, and react to the comment when it starts running (👀) and if the fix was successful (👍🏻) or not (😕).

- Update the `CHANGELOG.md`:

The nf-core-bot runs automatically on every PR updating the `CHANGELOG.md` if it was not updated. It will add the new change using the title of your PR.
If the action didn't run automatically, or you want to provide a different title, you can post a comment with:

```
@nf-core-bot changelog
```

Optionally followed by the description that you want to add to the changelog.

- Update Textual snapshots:

If the Textual snapshots (run by `tests/test_crate_app.py`) fail, an HTML report is generated and uploaded as an artifact.
If you are sure that these changes are correct, you can automatically update the snapshots form the PR by posting a comment with the magic words:

```
@nf-core-bot update snapshots
```

> [!WARNING]
> Please always check the HTML report to make sure that the changes are expected.
