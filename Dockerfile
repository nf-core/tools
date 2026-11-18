FROM python:3.14-slim@sha256:930e1abba7c4e8f96ed93e8012c35d174d7732752731bbd5e8e757d7ec6f3966
LABEL authors="phil.ewels@seqera.io,erik.danielsson@scilifelab.se" \
    description="Docker image containing requirements for nf-core/tools"

# Do not pick up python packages from $HOME
ENV PYTHONNUSERSITE=1

# Install uv
RUN python -m pip install --no-cache-dir uv

# Install Nextflow dependencies (headless Java: no desktop libraries needed)
# man dir is required for the Java installation
RUN mkdir -p /usr/share/man/man1 \
    && apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends git curl default-jre-headless \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install nf-test (pinned: avoids the installer's rate-limited GitHub API lookup, which 403s)
# renovate: datasource=github-releases depName=askimed/nf-test extractVersion=^v(?<version>.*)$
ARG NF_TEST_VERSION=0.9.5
RUN curl -fsSL https://get.nf-test.com | bash -s "${NF_TEST_VERSION}" \
    && mv nf-test /usr/local/bin \
    && chmod a+rx /usr/local/bin/nf-test

# Setup ARG for NXF_VER ENV (after nf-test, so changing it doesn't rebuild that layer)
ARG NXF_VER=""
ENV NXF_VER=${NXF_VER}
# Install Nextflow
RUN curl -s https://get.nextflow.io | bash \
    && mv nextflow /usr/local/bin \
    && chmod a+rx /usr/local/bin/nextflow

# Add the nf-core source files to the image
COPY . /usr/src/nf_core
WORKDIR /usr/src/nf_core

# Install nf-core
RUN uv pip install --system .

# Set up entrypoint and cmd for easy docker usage
ENTRYPOINT [ "nf-core" ]
CMD [ "." ]
