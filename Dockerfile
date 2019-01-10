FROM kleinstein/immcantation:2.6.0
LABEL authors="gisela.gabernet@qbic.uni-tuebingen.de, alexander.peltzer@qbic.uni-tuebingen.de" \
      description="Docker image containing base requirements for the nfcore pipelines"

# Install procps so that Nextflow can poll CPU usage
RUN dnf install -y bash
