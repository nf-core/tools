FROM gitpod/workspace-base

USER root

# Install util tools.
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
    graphviz

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
    conda install --quiet --yes --name base mamba && \
    mamba install --quiet --yes --name base \
    nextflow \
    nf-core \
    nf-test \
    black \
    prettier \
    pytest-workflow && \
    mamba clean --all -f -y

# Install nf-core
RUN python -m pip install .
