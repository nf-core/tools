FROM python:3.12-slim@sha256:740d94a19218c8dd584b92f804b1158f85b0d241e5215ea26ed2dcade2b9d138
LABEL authors="phil.ewels@seqera.io,erik.danielsson@scilifelab.se" \
    description="Docker image containing requirements for nf-core/tools"

# Do not pick up python packages from $HOME
ENV PYTHONNUSERSITE=1

# Update pip to latest version
RUN python -m pip install --upgrade pip

# Install dependencies
COPY requirements.txt requirements.txt
RUN python -m pip install -r requirements.txt

# Install Nextflow dependencies
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y git \
    && apt-get install -y curl

# Create man dir required for Java installation
# and install Java
RUN mkdir -p /usr/share/man/man1 \
    && apt-get install -y default-jre \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Setup ARG for NXF_VER ENV
ARG NXF_VER=""
ENV NXF_VER ${NXF_VER}
# Install Nextflow
RUN curl -s https://get.nextflow.io | bash \
    && mv nextflow /usr/local/bin \
    && chmod a+rx /usr/local/bin/nextflow
# Install nf-test
RUN curl -fsSL https://code.askimed.com/install/nf-test | bash \
    && mv nf-test /usr/local/bin \
    && chmod a+rx /usr/local/bin/nf-test

# Add the nf-core source files to the image
COPY . /usr/src/nf_core
WORKDIR /usr/src/nf_core

# Install nf-core
RUN python -m pip install .

# Set up entrypoint and cmd for easy docker usage
ENTRYPOINT [ "nf-core" ]
CMD [ "." ]
