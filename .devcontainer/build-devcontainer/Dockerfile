# devcontainers/miniconda image based on debian (bookworm)
# see tags and images: https://mcr.microsoft.com/en-us/artifact/mar/devcontainers/miniconda/tags
FROM "mcr.microsoft.com/devcontainers/miniconda@sha256:8e262a2664fab1d53054738d3633338558a2078ce66d3abde55c130f0d5da94f"

# copy this repo at current revision
COPY . /root/nfcore-tools/

# Explicitly reinstall python 3.13 via conda
# install local nf-core tools version, and precommit hooks
RUN cd /root/nfcore-tools/ && \
    conda install -y python=3.13 && \
    pip install --no-cache-dir --upgrade pip setuptools wheel pre-commit && \
    pip install -r requirements.txt -e . --no-cache-dir && \
    pre-commit install --install-hooks
