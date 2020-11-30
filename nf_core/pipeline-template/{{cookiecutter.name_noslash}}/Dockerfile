###################################################################################
##################################### WARNING #####################################
###################################################################################
## If using DSL2 then you no longer need this file unless you need to build and  ##
## host a custom container for your pipeline that contains software dependencies ##
## that are unavailable on Conda.                                                ##
##                                                                               ##
## All Conda dependencies can be installed by a combination of using:            ##
##   - The Nextflow 'conda' directive to list conda package requirements         ##
##   - The Nextflow 'container' directive to list Docker / Singularity images    ##
##     hosted by Biocontainers                                                   ##
##                                                                               ##
## See an example implementation of FastQC on nf-core/modules:                   ##
## https://github.com/nf-core/modules/blob/master/software/fastqc/main.nf        ##
###################################################################################

FROM nfcore/base:{{ 'dev' if 'dev' in cookiecutter.nf_core_version else cookiecutter.nf_core_version }}
LABEL authors="{{ cookiecutter.author }}" \
      description="Docker image containing all software requirements for the {{ cookiecutter.name }} pipeline"

# Install the conda environment
COPY environment.yml /
RUN conda env create --quiet -f /environment.yml && conda clean -a

# Add conda installation dir to PATH (instead of doing 'conda activate')
ENV PATH /opt/conda/envs/{{ cookiecutter.name_noslash }}-{{ cookiecutter.version }}/bin:$PATH

# Dump the details of the installed packages to a file for posterity
RUN conda env export --name {{ cookiecutter.name_noslash }}-{{ cookiecutter.version }} > {{ cookiecutter.name_noslash }}-{{ cookiecutter.version }}.yml

# Instruct R processes to use these empty files instead of clashing with a local version
RUN touch .Rprofile
RUN touch .Renviron
