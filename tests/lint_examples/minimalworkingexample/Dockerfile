FROM nfcore/base:dev
MAINTAINER Phil Ewels <phil.ewels@scilifelab.se>
LABEL authors="phil.ewels@scilifelab.se" \
    description="Docker image containing all requirements for the nf-core tools pipeline"

COPY environment.yml /
RUN conda env create --quiet -f /environment.yml && conda clean -a
RUN conda env export --name nf-core-tools-0.4 > nf-core-tools-0.4.yml
ENV PATH /opt/conda/envs/nf-core-tools-0.4/bin:$PATH
