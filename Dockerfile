FROM continuumio/miniconda:4.5.4
LABEL authors="phil.ewels@scilifelab.se,alexander.peltzer@qbic.uni-tuebingen.de" \
      description="Docker image containing base requirements for the nfcore pipelines"

# Install procps so that Nextflow can poll CPU usage
RUN apt-get update && apt-get install -y procps && apt-get clean -y 
RUN conda install conda=4.5.12
