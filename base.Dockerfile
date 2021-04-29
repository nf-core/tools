FROM continuumio/miniconda3:4.9.2
LABEL authors="phil.ewels@scilifelab.se,alexander.peltzer@boehringer-ingelheim.com" \
      description="Docker image containing base requirements for the nfcore pipelines"

# Install procps so that Nextflow can poll CPU usage and
# deep clean the apt cache to reduce image/layer size
RUN apt-get update \
      && apt-get install -y procps \
      && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Instruct R processes to use these empty files instead of clashing with a local version
RUN touch .Rprofile
RUN touch .Renviron
