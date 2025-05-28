# Test build locally before making a PR (from project root directory)
#   docker build . -t devcontainer:local -f nf_core/devcontainer/devcontainer.Dockerfile

# Uses mcr.microsoft.com/devcontainers/base:ubuntu
FROM ghcr.io/nextflow-io/training:latest

# Change user to vscode
USER vscode

# Change the nextflow directory
RUN chown -R vscode:vscode /usr/local/bin/ && \
    sudo chown -R vscode:vscode /opt/conda

# Add the nf-core source files to the image
COPY --chown=vscode:vscode . /usr/src/nf_core
WORKDIR /usr/src/nf_core

# Install nextflow and apptainer via conda
RUN conda install --quiet --yes --update-all --name base \
    conda-forge::apptainer>=1.4.1 && \
    conda clean --all --force-pkgs-dirs --yes
