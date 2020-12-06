#!/usr/bin/env python

import logging
import os
import nf_core

log = logging.getLogger(__name__)


def conda_dockerfile(self):
    """Checks the Docker build file.

    Checks that:
        * a name is given and is consistent with the pipeline name
        * dependency versions are pinned
        * dependency versions are the latest available
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
