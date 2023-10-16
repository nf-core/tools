FROM gitpod/workspace-base

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
    conda install --quiet --yes --name base mamba && \
    mamba install --quiet --yes --name base \
        nextflow \
        nf-core \
        nf-test \
        black \
        prettier \
        pre-commit \
        pytest-workflow && \
    mamba clean --all -f -y

# Update Nextflow
RUN nextflow self-update

# Install nf-core
RUN python -m pip install .
