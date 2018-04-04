FROM continuumio/miniconda
LABEL authors="phil.ewels@scilifelab.se,alexander.peltzer@qbic.uni-tuebingen.de" \
      description="Docker image containing base requirements for the nfcore pipelines"

# Install procps so that Nextflow can poll CPU usage
RUN apt-get update && apt-get install procps && apt-get purge
# Update the base version of conda
RUN conda update -n base conda
