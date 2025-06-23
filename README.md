<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/nf-core/tools/docs/images/nfcore-tools_logo_dark.png">
    <img alt="nf-core/tools" src="https://raw.githubusercontent.com/nf-core/tools/docs/images/nfcore-tools_logo_light.png">
  </picture>
</h1><!-- omit in toc -->

[![Python tests](https://github.com/nf-core/tools/workflows/Python%20tests/badge.svg?branch=main&event=push)](https://github.com/nf-core/tools/actions?query=workflow%3A%22Python+tests%22+branch%3Amain)
[![codecov](https://codecov.io/gh/nf-core/tools/branch/main/graph/badge.svg)](https://codecov.io/gh/nf-core/tools)
[![code style: prettier](https://img.shields.io/badge/code%20style-prettier-ff69b4.svg)](https://github.com/prettier/prettier)
[![code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json)](https://github.com/charliermarsh/ruff)

[![install with Bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](https://bioconda.github.io/recipes/nf-core/README.html)
[![install with PyPI](https://img.shields.io/badge/install%20with-PyPI-blue.svg)](https://pypi.org/project/nf-core/)
[![Get help on Slack](http://img.shields.io/badge/slack-nf--core%20%23tools-4A154B?logo=slack)](https://nfcore.slack.com/channels/tools)

A python package with helper tools for the nf-core community.

The nf-core tools package is written in Python and can be imported and used within other packages.
For documentation of the internal Python functions, please refer to the [Tools Python API docs](https://nf-co.re/tools/docs/).

## Installation

For full installation instructions, please see the [nf-core documentation](https://nf-co.re/docs/nf-core-tools/installation).
Below is a quick-start for those who know what they're doing:

### Bioconda

Install [from Bioconda](https://bioconda.github.io/recipes/nf-core/README.html):

```bash
conda install nf-core
```

Alternatively, you can create a new environment with both nf-core/tools and nextflow:

```bash
conda create --name nf-core python=3.13 nf-core nextflow
conda activate nf-core
```

### Python Package Index

Install [from PyPI](https://pypi.python.org/pypi/nf-core/):

```bash
pip install nf-core
```

### Development version

```bash
pip install --upgrade --force-reinstall git+https://github.com/nf-core/tools.git@dev
```

If editing, fork and clone the repo, then install as follows:

```bash
pip install --upgrade -r requirements-dev.txt -e .
```

## Contributions and Support

If you would like to contribute to this package, please see the [contributing guidelines](CONTRIBUTING.md).

For further information or help, don't hesitate to get in touch on the [Slack `#tools` channel](https://nfcore.slack.com/channels/tools) (you can join with [this invite](https://nf-co.re/join/slack)).

## Citation

If you use `nf-core tools` in your work, please cite the `nf-core` publication as follows:

> **The nf-core framework for community-curated bioinformatics pipelines.**
>
> Philip Ewels, Alexander Peltzer, Sven Fillinger, Harshil Patel, Johannes Alneberg, Andreas Wilm, Maxime Ulysse Garcia, Paolo Di Tommaso & Sven Nahnsen.
>
> _Nat Biotechnol._ 2020 Feb 13. doi: [10.1038/s41587-020-0439-x](https://dx.doi.org/10.1038/s41587-020-0439-x).
