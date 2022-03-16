# ![nf-core/tools](docs/images/nfcore-tools_logo_light.png#gh-light-mode-only) ![nf-core/tools](docs/images/nfcore-tools_logo_dark.png#gh-dark-mode-only) <!-- omit in toc -->

[![Python tests](https://github.com/nf-core/tools/workflows/Python%20tests/badge.svg?branch=master&event=push)](https://github.com/nf-core/tools/actions?query=workflow%3A%22Python+tests%22+branch%3Amaster)
[![codecov](https://codecov.io/gh/nf-core/tools/branch/master/graph/badge.svg)](https://codecov.io/gh/nf-core/tools)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[![install with Bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](https://bioconda.github.io/recipes/nf-core/README.html)
[![install with PyPI](https://img.shields.io/badge/install%20with-PyPI-blue.svg)](https://pypi.org/project/nf-core/)
[![Get help on Slack](http://img.shields.io/badge/slack-nf--core%20%23tools-4A154B?logo=slack)](https://nfcore.slack.com/channels/tools)

A python package with helper tools for the nf-core community.

> **Read this documentation on the nf-core website: [https://nf-co.re/tools](https://nf-co.re/tools)**

## Table of contents <!-- omit in toc -->

* [`nf-core` tools installation](#installation)
* [`nf-core list` - List available pipelines](#listing-pipelines)
* [`nf-core launch` - Run a pipeline with interactive parameter prompts](#launch-a-pipeline)
* [`nf-core download` - Download pipeline for offline use](#downloading-pipelines-for-offline-use)
* [`nf-core licences` - List software licences in a pipeline](#pipeline-software-licences)
* [`nf-core create` - Create a new pipeline with the nf-core template](#creating-a-new-pipeline)
* [`nf-core lint` - Check pipeline code against nf-core guidelines](#linting-a-workflow)
* [`nf-core schema` - Work with pipeline schema files](#pipeline-schema)
* [`nf-core bump-version` - Update nf-core pipeline version number](#bumping-a-pipeline-version-number)
* [`nf-core sync` - Synchronise pipeline TEMPLATE branches](#sync-a-pipeline-with-the-template)
* [`nf-core modules` - commands for dealing with DSL2 modules](#modules)
    * [`modules list` - List available modules](#list-modules)
        * [`modules list remote` - List remote modules](#list-remote-modules)
        * [`modules list local` - List installed modules](#list-installed-modules)
    * [`modules install` - Install modules in a pipeline](#install-modules-in-a-pipeline)
    * [`modules update` - Update modules in a pipeline](#update-modules-in-a-pipeline)
    * [`modules remove` - Remove a module from a pipeline](#remove-a-module-from-a-pipeline)
    * [`modules create` - Create a module from the template](#create-a-new-module)
    * [`modules create-test-yml` - Create the `test.yml` file for a module](#create-a-module-test-config-file)
    * [`modules lint` - Check a module against nf-core guidelines](#check-a-module-against-nf-core-guidelines)
    * [`modules bump-versions` - Bump software versions of modules](#bump-bioconda-and-container-versions-of-modules-in)

* [Citation](#citation)

The nf-core tools package is written in Python and can be imported and used within other packages.
For documentation of the internal Python functions, please refer to the [Tools Python API docs](https://nf-co.re/tools-docs/).

## Citation

If you use `nf-core tools` in your work, please cite the `nf-core` publication as follows:

> **The nf-core framework for community-curated bioinformatics pipelines.**
>
> Philip Ewels, Alexander Peltzer, Sven Fillinger, Harshil Patel, Johannes Alneberg, Andreas Wilm, Maxime Ulysse Garcia, Paolo Di Tommaso & Sven Nahnsen.
>
> _Nat Biotechnol._ 2020 Feb 13. doi: [10.1038/s41587-020-0439-x](https://dx.doi.org/10.1038/s41587-020-0439-x).
