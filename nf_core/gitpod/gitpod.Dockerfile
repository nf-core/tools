FROM gitpod/workspace-base

USER root

# Install Conda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda && \
    rm Miniconda3-latest-Linux-x86_64.sh

ENV PATH="/opt/conda/bin:$PATH"

RUN chown -R gitpod:gitpod /opt/conda

USER gitpod

# Install nextflow, nf-core, Mamba, and pytest-workflow
RUN conda update -n base -c defaults conda && \
    conda config --add channels defaults && \
    conda config --add channels bioconda && \
    conda config --add channels conda-forge && \
    conda install \
    openjdk=11.0.13 \
    nextflow=21.10.6 \
    pytest-workflow=1.6.0 \
    mamba=0.22.1 \
    pip=22.0.4 \
    black=22.1.0 \
    yamllint=1.26.3 \
    -n base && \
    nextflow self-update && \
    conda clean --all -f -y

# Add the nf-core source files to the image
COPY . /usr/src/nf_core
WORKDIR /usr/src/nf_core

# Install nf-core
RUN python -m pip install .
