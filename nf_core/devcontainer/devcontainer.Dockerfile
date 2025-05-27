# Test build locally before making a PR (from project root directory)
#   docker build . -t devcontainer:local -f nf_core/devcontainer/devcontainer.Dockerfile

# Uses mcr.microsoft.com/devcontainers/base:ubuntu
FROM ghcr.io/nextflow-io/training:latest

# Change user to vscode
USER vscode

# Add the nf-core source files to the image
COPY --chown=vscode:vscode . /usr/src/nf_core
WORKDIR /usr/src/nf_core

# Install nextflow and apptainer via conda
RUN sudo chown -R vscode:vscode /opt/conda && \
    conda install --quiet --yes --update-all --name base \
    conda-forge::apptainer>=1.4.1 && \
    conda clean --all --force-pkgs-dirs --yes

# Install nf-core with development dependencies and git commit hooks
RUN python -m pip install -r requirements-dev.txt -e . --no-cache-dir && \
    pre-commit install --install-hooks
