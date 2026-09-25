# devcontainers/miniconda image based on debian (bookworm)
# see tags and images: https://mcr.microsoft.com/en-us/artifact/mar/devcontainers/miniconda/tags
FROM mcr.microsoft.com/devcontainers/miniconda@sha256:617c7e42311066ac0bac3b7f0a3647daa9eec70fb8e3aeb8a5b083337a8a8687 AS build

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
FROM mcr.microsoft.com/devcontainers/base:2.1.13-debian12@sha256:73d85a96694a2cadca1ba3fcb5721f2312a64f1d571dd86f6c77e10a708931dc AS final

# Copy only the conda environment and site-packages from build stage
COPY --from=build /opt/conda /opt/conda
COPY --from=build /root/nfcore-tools/nf_core /root/nfcore-tools/nf_core

# Copy aptainer install from build stage
COPY --from=build /usr/local/apptainer /usr/local/apptainer
COPY --from=build /root/.bashrc /root/.bashrc
