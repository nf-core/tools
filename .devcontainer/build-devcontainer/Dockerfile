# devcontainers/miniconda image based on debian (bookworm)
# see tags and images: https://mcr.microsoft.com/en-us/artifact/mar/devcontainers/miniconda/tags
FROM mcr.microsoft.com/devcontainers/miniconda@sha256:1a85cf3e3da9d999f994f74cf501b1d02c9aa73ebfa3552f806dbe4570d7d5b5 AS build

# copy this repo at current revision
COPY . /root/nfcore-tools/

# Explicitly reinstall python 3.13 via conda
# Install uv and local nf-core tools version, and precommit hooks
RUN cd /root/nfcore-tools/ && \
    conda install -y python=3.13 && \
    pip install --no-cache-dir --upgrade pip uv && \
    uv pip install --system --no-cache-dir . && \
    rm -rf /root/.cache/pip /root/.cache/uv

# Install nextflow and nf-test via conda and run conda clean
RUN conda install -c bioconda -y nextflow nf-test && \
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
FROM mcr.microsoft.com/devcontainers/base:2.1.8-debian12@sha256:17e6cc517b483d1108b333d4c34352b0a21617f0117052e9b259d47113a9dc37 AS final

# Copy only the conda environment and site-packages from build stage
COPY --from=build /opt/conda /opt/conda
COPY --from=build /root/nfcore-tools/nf_core /root/nfcore-tools/nf_core

# Copy aptainer install from build stage
COPY --from=build /usr/local/apptainer /usr/local/apptainer
COPY --from=build /root/.bashrc /root/.bashrc
