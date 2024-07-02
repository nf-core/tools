# Test build locally before making a PR
#   docker build -t gitpod:test -f nf_core/gitpod/gitpod.Dockerfile .

FROM gitpod/workspace-base@sha256:0f3822450f94084f6a62db4a4282d895591f6a55632dc044fe496f98cb79e75c

USER root

# Install util tools.
# software-properties-common is needed to add ppa support for Apptainer installation
RUN apt-get update --quiet && \
    apt-get install --quiet --yes --no-install-recommends \
    apt-transport-https \
    apt-utils \
    sudo \
    git \
    less \
    wget \
    curl \
    tree \
    graphviz \
    software-properties-common && \
    add-apt-repository -y ppa:apptainer/ppa && \
    apt-get update --quiet && \
    apt-get install --quiet --yes apptainer && \
    wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda && \
    rm Miniconda3-latest-Linux-x86_64.sh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set PATH for Conda
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
    nextflow \
    nf-test \
    prettier \
    pre-commit \
    ruff \
    mypy \
    openjdk \
    pytest-workflow && \
    conda clean --all --force-pkgs-dirs --yes

# Update Nextflow and Install nf-core
RUN nextflow self-update && \
    python -m pip install . --no-cache-dir

# Setup pdiff for nf-test diffs
ENV NFT_DIFF="pdiff"
ENV NFT_DIFF_ARGS="--line-numbers --expand-tabs=2"
