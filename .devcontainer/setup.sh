#!/usr/bin/env bash

# Customise the terminal command prompt
echo "export PROMPT_DIRTRIM=2" >> $HOME/.bashrc
echo "export PS1='\[\e[3;36m\]\w ->\[\e[0m\\] '" >> $HOME/.bashrc
export PROMPT_DIRTRIM=2
export PS1='\[\e[3;36m\]\w ->\[\e[0m\\] '

# Update Nextflow
nextflow self-update

# Install specifically the version of tools from the workspace
uv sync

# Activate the virtual environment automatically on login
echo "source $(pwd)/.venv/bin/activate" >> $HOME/.bashrc

# Install pre-commit hooks (using the venv)
source .venv/bin/activate
prek install --install-hooks

# Update welcome message
echo "Welcome to the nf-core devcontainer!" > /usr/local/etc/vscode-dev-containers/first-run-notice.txt
