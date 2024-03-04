# Test build locally before making a PR
#   docker build -t gitpod:test -f nf_core/gitpod/gitpod.Dockerfile .

FROM gitpod/workspace-base@sha256:c15ee2f4de8902421ccbfbd77329a9e8e4abf18477e1b5ae8a1a572790254647

USER root

# Install util tools.
# software-properties-common is needed to add ppa support for Apptainer installation
RUN apt-get update --quiet && \
    apt-get install --quiet --yes \
    apt-transport-https \
    apt-utils \
    sudo \
    git \
    less \
    wget \
    curl \
    tree \
    graphviz \
    software-properties-common

# Install Apptainer (Singularity)
RUN add-apt-repository -y ppa:apptainer/ppa && \
    apt-get update --quiet && \
    apt install -y apptainer

# Install Conda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda && \
    rm Miniconda3-latest-Linux-x86_64.sh

ENV PATH="/opt/conda/bin:$PATH"

# Add the nf-core source files to the image
COPY . /usr/src/nf_core
WORKDIR /usr/src/nf_core

# Change ownership for gitpod
RUN chown -R gitpod:gitpod /opt/conda /usr/src/nf_core

# Change user to gitpod
USER gitpod
# Install nextflow, nf-core, Mamba, and pytest-workflow
RUN conda config --add channels defaults && \
    conda config --add channels bioconda && \
    conda config --add channels conda-forge && \
    conda config --set channel_priority strict && \
    conda install --quiet --yes --name base \
    mamba \
    nextflow \
    nf-core \
    nf-test \
    prettier \
    pre-commit \
    ruff \
    openjdk \
    pytest-workflow && \
    conda clean --all --force-pkgs-dirs --yes

# Update Nextflow
RUN nextflow self-update

# Install nf-core
RUN python -m pip install . --no-cache-dir

# Setup pdiff for nf-test diffs
RUN export NFT_DIFF="pdiff" && \
    export NFT_DIFF_ARGS="--line-numbers --expand-tabs=2"
