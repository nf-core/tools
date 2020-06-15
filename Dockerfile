FROM continuumio/miniconda3:4.7.12
LABEL authors="phil.ewels@scilifelab.se,alexander.peltzer@qbic.uni-tuebingen.de" \
      description="Docker image containing base requirements for the nfcore pipelines"

# Install procps so that Nextflow can poll CPU usage
RUN apt-get update && apt-get install -y procps && apt-get clean -y
RUN conda update -n base -c defaults conda=4.8.3
