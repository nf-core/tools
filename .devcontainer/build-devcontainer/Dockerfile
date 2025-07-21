# ubuntu 22.04
FROM "mcr.microsoft.com/devcontainers/base@sha256:e57fdff274ed0bac0776490fa2644c242491bb21d4df7ad0bb79b433eac5168d"

# copy this repo at current revision
COPY . /root/nfcore-tools/

# install python 3.11, local nf-core tools version, and precommit hooks
RUN cd /root/nfcore-tools/ && \
    apt-get update && \
    apt-get install -yq --no-install-recommends python3.11 python3-pip python3-venv && \
    pip3 install --no-cache-dir --upgrade pip setuptools wheel pre-commit && \
    pip3 install -r requirements.txt -e . --no-cache-dir && \
    pre-commit install --install-hooks
