#!/usr/bin/env bash

# Install conda packages needed for Nextflow Training

conda config --add channels bioconda
conda config --add channels conda-forge
conda config --set channel_priority strict
