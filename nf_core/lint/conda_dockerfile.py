#!/usr/bin/env python


def conda_dockerfile(self):
    """Checks the Docker build file.

    Checks that:
        * a name is given and is consistent with the pipeline name
        * dependency versions are pinned
        * dependency versions are the latest available
    """
    passed = []
    warned = []
    failed = []

    if "environment.yml" not in self.files or "Dockerfile" not in self.files or len(self.dockerfile) == 0:
        return

    expected_strings = [
        "COPY environment.yml /",
        "RUN conda env create --quiet -f /environment.yml && conda clean -a",
        "RUN conda env export --name {} > {}.yml".format(self.conda_config["name"], self.conda_config["name"]),
        "ENV PATH /opt/conda/envs/{}/bin:$PATH".format(self.conda_config["name"]),
    ]

    if "dev" not in self.version:
        expected_strings.append("FROM nfcore/base:{}".format(self.version))

    difference = set(expected_strings) - set(self.dockerfile)
    if not difference:
        passed.append("Found all expected strings in Dockerfile file")
    else:
        for missing in difference:
            failed.append("Could not find Dockerfile file string: {}".format(missing))

    return {"passed": passed, "warned": warned, "failed": failed}
