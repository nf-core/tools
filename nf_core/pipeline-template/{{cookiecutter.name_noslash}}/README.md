# {{ cookiecutter.name }}

**{{ cookiecutter.description }}**.

[![Build Status](https://travis-ci.com/{{ cookiecutter.name }}.svg?branch=master)](https://travis-ci.com/{{ cookiecutter.name }})
[![Nextflow](https://img.shields.io/badge/nextflow-%E2%89%A50.32.0-brightgreen.svg)](https://www.nextflow.io/)

[![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](http://bioconda.github.io/)
[![Docker](https://img.shields.io/docker/automated/{{ cookiecutter.name_docker }}.svg)](https://hub.docker.com/r/{{ cookiecutter.name_docker }})
![Singularity Container available](
https://img.shields.io/badge/singularity-available-7E4C74.svg)

## Introduction
The pipeline is built using [Nextflow](https://www.nextflow.io), a workflow tool to run tasks across multiple compute infrastructures in a very portable manner. It comes with docker / singularity containers making installation trivial and results highly reproducible.


## Documentation
The {{ cookiecutter.name }} pipeline comes with documentation about the pipeline, found in the `docs/` directory:

1. [Installation](docs/installation.md)
2. Pipeline configuration
    * [Local installation](docs/configuration/local.md)
    * [Adding your own system](docs/configuration/adding_your_own.md)
    * [Reference genomes](docs/configuration/reference_genomes.md)  
3. [Running the pipeline](docs/usage.md)
4. [Output and how to interpret the results](docs/output.md)
5. [Troubleshooting](docs/troubleshooting.md)

<!-- TODO nf-core: Add a brief overview of what the pipeline does and how it works -->

## Credits
{{ cookiecutter.name }} was originally written by {{ cookiecutter.author }}.
