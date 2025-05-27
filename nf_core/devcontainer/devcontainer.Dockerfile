# Test build locally before making a PR (from project root directory)
#   docker build . -t devcontainer:local -f nf_core/devcontainer/devcontainer.Dockerfile

# See https://docs.renovatebot.com/docker/#digest-pinning for why a digest is used.
FROM mcr.microsoft.com/devcontainers/python:3.11

USER root

# Install util tools.
RUN apt-get update --quiet && \
    apt-get install --quiet --yes --no-install-recommends \
    apt-transport-https \
    apt-utils \
    graphviz && \
    wget --quiet https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh && \
    bash Miniforge3-Linux-x86_64.sh -b -p /opt/conda && \
    rm Miniforge3-Linux-x86_64.sh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set PATH for Conda
ENV PATH="/opt/conda/bin:$PATH"

# Add the nf-core source files to the image
COPY --chown=vscode:vscode . /usr/src/nf_core
WORKDIR /usr/src/nf_core

# Change user to gitpod
USER vscode

# Install nextflow, nf-core, nf-test, and other useful tools
RUN chown -R vscode:vscode /opt/conda && \
    conda config --add channels bioconda && \
    conda config --add channels conda-forge && \
    conda config --set channel_priority strict && \
    conda install --quiet --yes --update-all --name base \
    apptainer \
    nextflow && \
    conda clean --all --force-pkgs-dirs --yes

# Update Nextflow and Install nf-core
# TODO: This adds 900MB to the image
# RUN nextflow self-update && \
#     python -m pip install -r requirements-dev.txt -e . --no-cache-dir && \
#     pre-commit install --install-hooks
