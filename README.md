<img src="https://nf-core.github.io/assets/logo/nf-core-logo.png" width="400">

# [nf-core/tools](https://github.com/nf-core/tools)
A python package with helper tools for the nf-core community.

## Installation
Install the package with the following command:

```
pip install --upgrade --force-reinstall git+https://github.com/nf-core/tools.git
```

Alternatively, if you would like to edit the files locally:

```bash
# You should probably specify your fork instead
git clone https://github.com/nf-core/tools.git nf-core-tools
cd nf-core-tools
python setup.py develop
# Or with pip
pip install -e .
```

## Linting
The `lint` subcommand checks a given pipeline for all nf-core community guidelines.
This is the same test that is used on the automated continuous integration tests.

For example, the current version looks something like this:

```bash
$ cd path/to/my_pipeline
$ nf-core lint .
```
```
INFO:root:Checking required files exist
INFO:root:Checking pipeline config variables
INFO:root:
=================
 LINTING RESULTS
=================

   10 tests passed
    1 tests had warnings
    1 tests failed

Warnings:
  https://nf-core.github.io/errors#1: File not found: tests/run_test.sh

Failures:
  https://nf-core.github.io/errors#1: File not found: LICENSE


INFO:root:Sorry, some tests failed - exiting with a non-zero error code...
```
