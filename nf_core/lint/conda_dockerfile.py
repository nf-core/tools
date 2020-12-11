#!/usr/bin/env python

import logging
import os
import nf_core

log = logging.getLogger(__name__)


def conda_dockerfile(self):
    """Checks the Dockerfile for use with Conda environments

    .. note:: This test only runs if there is both an ``environment.yml``
              and ``Dockerfile`` present in the pipeline root directory.

    If a workflow has a conda ``environment.yml`` file, the ``Dockerfile`` should use this
    to create the docker image. These files are typically very short, just creating the conda
    environment inside the container.

    This linting test checks for the following:

    * All of the following lines are present in the file (where ``PIPELINE`` is your pipeline name):

        .. code-block:: Dockerfile

           FROM nfcore/base:VERSION
           COPY environment.yml /
           RUN conda env create --quiet -f /environment.yml && conda clean -a
           RUN conda env export --name PIPELINE > PIPELINE.yml
           ENV PATH /opt/conda/envs/PIPELINE/bin:$PATH

    * That the ``FROM nfcore/base:VERSION`` is tagged to the most recent release of nf-core/tools

        * The linting tool compares the tag against the currently installed version of tools.
        * This line is not checked if running a development version of nf-core/tools.

    .. tip:: Additional lines and different metadata can be added to the ``Dockerfile``
                 without causing this lint test to fail.
    """

    # Check if we have both a conda and dockerfile
    if self._fp("environment.yml") not in self.files or self._fp("Dockerfile") not in self.files:
        return {"ignored": ["No `environment.yml` / `Dockerfile` file found - skipping conda_dockerfile test"]}

    expected_strings = [
        "COPY environment.yml /",
        "RUN conda env create --quiet -f /environment.yml && conda clean -a",
        "RUN conda env export --name {} > {}.yml".format(self.conda_config["name"], self.conda_config["name"]),
        "ENV PATH /opt/conda/envs/{}/bin:$PATH".format(self.conda_config["name"]),
    ]

    if "dev" not in nf_core.__version__:
        expected_strings.append("FROM nfcore/base:{}".format(nf_core.__version__))

    with open(os.path.join(self.wf_path, "Dockerfile"), "r") as fh:
        dockerfile_contents = fh.read().splitlines()

    difference = set(expected_strings) - set(dockerfile_contents)
    if not difference:
        return {"passed": ["Found all expected strings in Dockerfile file"]}
    else:
        return {"failed": ["Could not find Dockerfile file string: `{}`".format(missing) for missing in difference]}
