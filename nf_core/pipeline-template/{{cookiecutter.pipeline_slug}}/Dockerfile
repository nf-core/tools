FROM nfcore/base
LABEL description="Docker image containing all requirements for {{ cookiecutter.pipeline_name }} pipeline"

COPY environment.yml /
RUN conda env create -f /environment.yml && conda clean -a
ENV PATH /opt/conda/envs/nfcore-{{ cookiecutter.pipeline_slug }}-{{ cookiecutter.version }}/bin:$PATH
