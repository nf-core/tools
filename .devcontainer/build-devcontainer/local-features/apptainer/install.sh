#!/usr/bin/env bash

# Install Apptainer (Singularity)

apt-get update --quiet

# apptainer installer dependencies
apt-get install -y curl rpm2cpio cpio

# install from pre-built binaries
# see: https://apptainer.org/docs/admin/main/installation.html#install-unprivileged-from-pre-built-binaries
curl -s https://raw.githubusercontent.com/apptainer/apptainer/main/tools/install-unprivileged.sh | bash -s - /usr/local/apptainer

# add /usr/local/apptainer/bin to path
echo "PATH=/usr/local/apptainer/bin:$PATH" >> $HOME/.bashrc

apt-get clean
rm -rf /var/lib/apt/lists/*
