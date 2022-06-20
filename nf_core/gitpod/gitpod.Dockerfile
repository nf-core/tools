FROM gitpod/workspace-base

USER root

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
RUN conda update -n base -c defaults conda && \
    conda config --add channels defaults && \
    conda config --add channels bioconda && \
    conda config --add channels conda-forge && \
    conda install \
        openjdk=11.0.13 \
        nextflow=22.04.0 \
        pytest-workflow=1.6.0 \
        mamba=0.23.1 \
        pip=22.0.4 \
        black=22.1.0 \
        -n base && \
    conda clean --all -f -y

# Install nf-core
RUN python -m pip install .
