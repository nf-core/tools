# nf-core/tools: Contributing Guidelines

Hi there! Many thanks for taking an interest in improving nf-core/tools.

If you need help then the best place to ask is the [`#tools` channel](https://nfcore.slack.com/channels/tools) on the nf-core Slack.
You can get an invite on the [nf-core website](https://nf-co.re/join/slack/).

## Contribution workflow

If you'd like to write some code for nf-core/tools, the standard workflow
is as follows:

1. Check that there isn't [already an issue](https://github.com/nf-core/tools/issues) about your idea to avoid duplicating work.
    * If there isn't one already, please create one so that others know you're working on this
2. Fork the [nf-core/tools repository](https://github.com/nf-core/tools) to your GitHub account
3. Make the necessary changes / additions within your forked repository
4. Submit a Pull Request against the `dev` branch and wait for the code to be reviewed and merged.

If you're not used to this workflow with git, you can start with some [basic docs from GitHub](https://help.github.com/articles/fork-a-repo/).

## Code formatting with Black

All Python code in nf-core/tools must be passed through the [Black Python code formatter](https://black.readthedocs.io/en/stable/).
This ensures a harmonised code formatting style throughout the package, from all contributors.

You can run Black on the command line - first install using `pip` and then run recursively on the whole repository:

```bash
pip install black
black .
```

Alternatively, Black has [integrations for most common editors](https://black.readthedocs.io/en/stable/editor_integration.html)
to automatically format code when you hit save.
You can also set it up to run when you [make a commit](https://black.readthedocs.io/en/stable/version_control_integration.html).

There is an automated CI check that runs when you open a pull-request to nf-core/tools that will fail if
any code does not adhere to Black formatting.

## API Documentation

We aim to write function docstrings according to the [Google Python style-guide](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings). These are used to automatically generate package documentation on the nf-core website using Sphinx.
You can find this documentation here: [https://nf-co.re/tools-docs/](https://nf-co.re/tools-docs/)

If you would like to test the documentation, you can install Sphinx locally by following Sphinx's [installation instruction](https://www.sphinx-doc.org/en/master/usage/installation.html).
Once done, you can run `make clean` and then `make html` in the root directory of `nf-core tools`.
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
pip install --upgrade pip pytest pytest-datafiles pytest-cov mock
pytest --color=yes tests/
```

### Lint Tests

nf-core/tools contains both the main nf-core template for pipelines and the code used to test that pipelines adhere to the nf-core guidelines.
As these two commonly need to be edited together, we test the creation of a pipeline and then linting using a CI check.
This ensures that any changes we make to either the linting or the template stay in sync.
You can replicate this process locally with the following commands:

```bash
nf-core create -n testpipeline -d "This pipeline is for testing"
nf-core lint nf-core-testpipeline
```
