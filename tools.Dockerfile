FROM python:3.8.9-slim 
LABEL authors="phil.ewels@scilifelab.se,erik.danielsson@scilifelab.se" \
      description="Docker image containing requirements for the nfcore tools"

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
      && apt-get install -y  openjdk-11-jre \
      && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install Nextflow
RUN curl -s https://get.nextflow.io | bash \
      && mv nextflow /usr/local/bin \
      && chmod a+rx /usr/local/bin/nextflow
# Add the nf-core source files to the image
COPY . /usr/src/nf_core
WORKDIR /usr/src/nf_core

# Install nf-core
RUN python -m pip install .

# Set up entrypoint and cmd for easy docker usage
ENTRYPOINT [ "nf-core" ]
CMD [ "." ]
