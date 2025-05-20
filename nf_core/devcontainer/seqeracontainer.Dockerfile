FROM community.wave.seqera.io/library/nextflow_nf-test_apptainer_curl_pruned:eeb39fa4eeaed3f3

RUN curl -sSL https://get.docker.com/ | sh

# Add the nf-core source files to the image
COPY . /usr/src/nf_core
WORKDIR /usr/src/nf_core

# Update Nextflow and Install nf-core
RUN python -m pip install . --no-cache-dir

# Setup pdiff for nf-test diffs
ENV NFT_DIFF="pdiff"
ENV NFT_DIFF_ARGS="--line-numbers --expand-tabs=2"
ENV JAVA_TOOL_OPTIONS=
