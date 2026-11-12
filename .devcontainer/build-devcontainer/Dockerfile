# devcontainers/miniconda image based on debian (bookworm)
# see tags and images: https://mcr.microsoft.com/en-us/artifact/mar/devcontainers/miniconda/tags
FROM mcr.microsoft.com/devcontainers/miniconda@sha256:c8a96d3426476d967a14b03a65b2914a4149de3f79c01741d38dc6f14c7c6d00 AS build

# Replace the Anaconda defaults channels (which require accepting their Terms of Service)
# with conda-forge and bioconda. Uses --system because defaults is set in /opt/conda/.condarc
RUN conda config --system --remove channels defaults && \
    conda config --system --add channels bioconda && \
    conda config --system --add channels conda-forge && \
    conda config --system --set channel_priority strict

# copy this repo at current revision
COPY . /root/nfcore-tools/

# Explicitly install python 3.14 via conda (the image's Anaconda packages are built for 3.14)
# Install uv and local nf-core tools version, and precommit hooks
RUN cd /root/nfcore-tools/ && \
    conda install -y python=3.14 && \
    pip install --no-cache-dir --upgrade pip uv && \
    uv pip install --system --no-cache-dir . && \
    rm -rf /root/.cache/pip /root/.cache/uv

# Install nextflow and nf-test via conda and run conda clean
RUN conda install -y nextflow nf-test && \
    conda clean -afy

# Install dependencies for apptainer build and apptainer and run apt clean
RUN rm -f /etc/apt/sources.list.d/yarn.list && \
    apt-get update --quiet && \
    apt-get install -y curl rpm2cpio cpio && \
    curl -s https://raw.githubusercontent.com/apptainer/apptainer/main/tools/install-unprivileged.sh | bash -s - /usr/local/apptainer && \
    echo "PATH=/usr/local/apptainer/bin:$PATH" >> $HOME/.bashrc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Final stage to copy only the required files after installation
FROM mcr.microsoft.com/devcontainers/base:2.2.5-debian12@sha256:99f5250dd2d5f8b11046d5662dd94c1e3c1dae56b560c7caad5ceb7edf349046 AS final

# Copy only the conda environment and site-packages from build stage
COPY --from=build /opt/conda /opt/conda
COPY --from=build /root/nfcore-tools/nf_core /root/nfcore-tools/nf_core

# Copy aptainer install from build stage
COPY --from=build /usr/local/apptainer /usr/local/apptainer
COPY --from=build /root/.bashrc /root/.bashrc
