# {{ cookiecutter.pipeline_name }}
{{ cookiecutter.pipeline_short_description }}

[![Build Status](https://travis-ci.org/nf-core/{{ cookiecutter.pipeline_name }}.svg?branch=master)](https://travis-ci.org/nf-core/{{ cookiecutter.pipeline_name }})
[![Nextflow](https://img.shields.io/badge/nextflow-%E2%89%A50.30.0-brightgreen.svg)](https://www.nextflow.io/)

[![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](http://bioconda.github.io/)
[![Docker](https://img.shields.io/docker/automated/{{ cookiecutter.pipeline_slug }}.svg)](https://hub.docker.com/r/{{ cookiecutter.pipeline_slug }})
![Singularity Container available](
https://img.shields.io/badge/singularity-available-7E4C74.svg)

### Introduction
{{ cookiecutter.pipeline_name }}: {{ cookiecutter.pipeline_short_description }}

The pipeline is built using [Nextflow](https://www.nextflow.io), a workflow tool to run tasks across multiple compute infrastructures in a very portable manner. It comes with docker / singularity containers making installation trivial and results highly reproducible.


### Documentation
The {{ cookiecutter.pipeline_name }} pipeline comes with documentation about the pipeline, found in the `docs/` directory:

1. [Installation](docs/installation.md)
2. Pipeline configuration
    * [Local installation](docs/configuration/local.md)
    * [Adding your own system](docs/configuration/adding_your_own.md)
3. [Running the pipeline](docs/usage.md)
4. [Output and how to interpret the results](docs/output.md)
5. [Troubleshooting](docs/troubleshooting.md)
