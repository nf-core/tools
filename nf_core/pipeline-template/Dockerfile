FROM nfcore/base:{{ 'dev' if 'dev' in nf_core_version else nf_core_version }}
LABEL authors="{{ author }}" \
      description="Docker image containing all software requirements for the {{ name }} pipeline"

# Install the conda environment
COPY environment.yml /
RUN conda env create --quiet -f /environment.yml && conda clean -a

# Add conda installation dir to PATH (instead of doing 'conda activate')
ENV PATH /opt/conda/envs/{{ name_noslash }}-{{ version }}/bin:$PATH

# Dump the details of the installed packages to a file for posterity
RUN conda env export --name {{ name_noslash }}-{{ version }} > {{ name_noslash }}-{{ version }}.yml
