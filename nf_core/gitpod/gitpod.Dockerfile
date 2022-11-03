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
        openjdk=17.0.3 \
        nextflow=22.10.0 \
        nf-test=0.7.0 \
        pytest-workflow=1.6.0 \
        mamba=0.27.0 \
        pip=22.3 \
        black=22.10.0 \
        prettier=2.7.1 \
        -n base && \
    conda clean --all -f -y

# Install nf-core
RUN python -m pip install .
