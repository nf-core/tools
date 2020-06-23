FROM continuumio/miniconda3:4.7.12
LABEL authors="phil.ewels@scilifelab.se,alexander.peltzer@qbic.uni-tuebingen.de" \
      description="Docker image containing base requirements for the nfcore pipelines"


RUN apt-get update && apt-get install -y procps && apt-get clean -y

# Install procps so that Nextflow can poll CPU usage and 
# deep clean the apt cache to reduce image/layer size
RUN apt-get update \
 && apt-get install -y procps \
 && apt-get clean && rm -rf /var/lib/apt/lists/*