# nf-core/tools: Contributing Guidelines

Hi there! Many thanks for taking an interest in improving nf-core/tools.

We try to manage the required tasks for nf-core/tools using GitHub issues, you probably came to this page when creating one. Please use the pre-filled templates to save time.

However, don't be put off by this template - other more general issues and suggestions are welcome! Contributions to the code are even more welcome ;)

> If you need help using or developing nf-core/tools then the best place to go is the Gitter chatroom where you can ask us questions directly: https://gitter.im/nf-core/Lobby

## Contribution workflow
If you'd like to write some code for nf-core/tools, the standard workflow
is as follows:

1. Check that there isn't already an issue about your idea in the
   [nf-core/tools issues](https://github.com/nf-core/tools/issues) to avoid
   duplicating work.
    * If there isn't one already, please create one so that others know you're working on this
2. Fork the [nf-core/tools repository](https://github.com/nf-core/tools) to your GitHub account
3. Make the necessary changes / additions within your forked repository
4. Submit a Pull Request against the `dev` branch and wait for the code to be reviewed and merged.

If you're not used to this workflow with git, you can start with some [basic docs from GitHub](https://help.github.com/articles/fork-a-repo/) or even their [excellent interactive tutorial](https://try.github.io/).

## Style guide
Google provides an excellent [style guide](https://github.com/google/styleguide/blob/gh-pages/pyguide.md), which
is an best practise extension of [PEP](https://www.python.org/dev/peps/), the Python Enhancement Proposals. Have a look at the 
[docstring](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings) section, which is in particular
important, as nf-core tool's code documentation is generated out of these automatically.

In order to test the documentation, you have to install Sphinx on the machine, where the documentation should be generated.

Please follow Sphinx's [installation instruction](http://www.sphinx-doc.org/en/master/usage/installation.html).

Once done, you can run `make clean` and then `make html` in the root directory of `nf-core tools`, where the `Makefile` is located.

The HTML will then be generated in `docs/api/_build/html`.


## Tests
When you create a pull request with changes, [Travis CI](https://travis-ci.org/) will run automatic tests.
Typically, pull-requests are only fully reviewed when these tests are passing, though of course we can help out before then.

There are two types of tests that run:

### Unit Tests
The nf-core tools package has a set of unit tests bundled, which can be found in the `tests/` directory.
New features should also come with new tests, to keep the test-coverage high (we use [codecov.io](https://codecov.io/gh/nf-core/tools/) to check this automatically).

You can try running the tests locally before pushing code using the following command:

```bash
python -m pytest .
```

### Lint Tests
The nf-core has a [set of guidelines](http://nf-co.re/guidelines) which all pipelines must adhere to.
To enforce these and ensure that all pipelines stay in sync, we have developed a helper tool which runs checks on the pipeline code. This is in the [nf-core/tools repository](https://github.com/nf-core/tools) and once installed can be run locally with the `nf-core lint <pipeline-directory>` command.

The nf-core/tools repo itself contains the master template for creating new nf-core pipelines.
Travis is set up to create a new pipeline from this template and then run the lint tests on it.
This ensures that any changes we make to either the linting or the template stay in sync.
You can replicate this process locally with the following commands:

```bash
nf-core create -n testpipeline -d "This pipeline is for testing"
nf-core lint nf-core-testpipeline
```

## Getting help
For further information/help, please consult the [nf-core/tools documentation](https://github.com/nf-core/tools#documentation) and don't hesitate to get in touch on [Gitter](https://gitter.im/nf-core/Lobby)
