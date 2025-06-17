#!/usr/bin/env bash

# Customise the terminal command prompt
printf "export PS1='\\[\\e[3;36m\\]\${PWD#/workspaces/} ->\\[\\e[0m\\] '\n" >> $HOME/.bashrc
export PS1='\[\e[3;36m\]${PWD#/workspaces/} ->\[\e[0m\] '

# Update Nextflow
nextflow self-update

# Install nf-core tools in editable mode
python -m pip install -r requirements-dev.txt -e . --no-cache-dir

# Install pre-commit hooks
pre-commit install --install-hooks
