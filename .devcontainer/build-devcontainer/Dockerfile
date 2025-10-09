# devcontainers/miniconda image based on debian (bookworm)
# see tags and images: https://mcr.microsoft.com/en-us/artifact/mar/devcontainers/miniconda/tags
FROM "mcr.microsoft.com/devcontainers/miniconda@sha256:8e262a2664fab1d53054738d3633338558a2078ce66d3abde55c130f0d5da94f" AS build

# copy this repo at current revision
COPY . /root/nfcore-tools/

# Explicitly reinstall python 3.14 via conda
# install local nf-core tools version, and precommit hooks
RUN cd /root/nfcore-tools/ && \
    conda install -y python=3.14 && \
    pip install --no-cache-dir --upgrade pip setuptools wheel pre-commit && \
    pip install -r requirements.txt --no-cache-dir -e . && \
    pre-commit install --install-hooks && \
    rm -rf /root/.cache/pip

# Install nextflow and nf-test via conda and run conda clean
RUN conda install -c bioconda -y nextflow nf-test && \
    conda clean -afy

# Install dependencies for apptainer build and apptainer and run apt clean
RUN apt-get update --quiet && \
    apt-get install -y curl rpm2cpio cpio && \
    curl -s https://raw.githubusercontent.com/apptainer/apptainer/main/tools/install-unprivileged.sh | bash -s - /usr/local/apptainer && \
    echo "PATH=/usr/local/apptainer/bin:$PATH" >> $HOME/.bashrc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Final stage to copy only the required files after installation
FROM "mcr.microsoft.com/devcontainers/base:debian@sha256:ce2e9e611939e611b737362c045bb6d3449bb3efb84898525d724aace1737b90" AS final

# Copy only the conda environment and site-packages from build stage
COPY --from=build /opt/conda /opt/conda
COPY --from=build /root/nfcore-tools/nf_core /root/nfcore-tools/nf_core

# Copy aptainer install from build stage
COPY --from=build /usr/local/apptainer /usr/local/apptainer
COPY --from=build /root/.bashrc /root/.bashrc
