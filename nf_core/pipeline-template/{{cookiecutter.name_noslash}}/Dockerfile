FROM nfcore/base:{{ 'dev' if 'dev' in cookiecutter.nf_core_version else cookiecutter.nf_core_version }}
LABEL authors="{{ cookiecutter.author }}" \
      description="Docker image containing all requirements for {{ cookiecutter.name }} pipeline"

COPY environment.yml /
RUN conda env create -f /environment.yml && conda clean -a
ENV PATH /opt/conda/envs/{{ cookiecutter.name_noslash }}-{{ cookiecutter.version }}/bin:$PATH
