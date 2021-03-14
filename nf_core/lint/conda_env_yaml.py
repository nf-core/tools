#!/usr/bin/env python

import logging
import os
import requests
import yaml
import nf_core.utils

from nf_core.utils import anaconda_package

# Set up local caching for requests to speed up remote queries
nf_core.utils.setup_requests_cachedir()

# Don't pick up debug logs from the requests package
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

log = logging.getLogger(__name__)


def conda_env_yaml(self):
    """Checks that the conda environment file is valid.

    .. note:: This test is ignored if there is not an ``environment.yml``
              file present in the pipeline root directory.

    DSL1 nf-core pipelines use a single Conda environment to manage all software
    dependencies for a workflow. This can be used directly with ``-profile conda``
    and is also used in the ``Dockerfile`` to build a docker image.

    This test checks the conda ``environment.yml`` file to ensure that it follows nf-core guidelines.
    Each dependency is checked using the `Anaconda API service <https://api.anaconda.org/docs>`_.
    Dependency sublists are ignored with the exception of ``- pip``: these packages are also checked
    for pinned version numbers and checked using the `PyPI JSON API <https://wiki.python.org/moin/PyPIJSON>`_.

    Specifically, this lint test makes sure that:

    * The environment ``name`` must match the pipeline name and version

        * The pipeline name is defined in the config variable ``manifest.name``
        * Replace the slash with a hyphen as environment names shouldn't contain that character
        * Example: For ``nf-core/test`` version 1.4, the conda environment name should be ``nf-core-test-1.4``

    * All package dependencies have a specific version number pinned

        .. warning:: Remember that Conda package versions should be pinned with one equals sign (``toolname=1.1``),
                 but pip uses two (``toolname==1.2``)

    * That package versions can be found and are the latest available

        * Test will go through all conda channels listed in the file, or check PyPI if ``pip``
        * Conda dependencies with pinned channels (eg. ``conda-forge::openjdk``) are ok too
        * In addition to the package name, the pinned version is checked
        * If a newer version is available, a warning will be reported
    """
    passed = []
    warned = []
    failed = []
    fixed = []
    could_fix = False

    env_path = os.path.join(self.wf_path, "environment.yml")
    if env_path not in self.files:
        return {"ignored": ["No `environment.yml` file found - skipping conda_env_yaml test"]}

    with open(env_path, "r") as fh:
        raw_environment_yml = fh.read()

    # Check that the environment name matches the pipeline name
    pipeline_version = self.nf_config.get("manifest.version", "").strip(" '\"")
    expected_env_name = "nf-core-{}-{}".format(self.pipeline_name.lower(), pipeline_version)
    if self.conda_config["name"] != expected_env_name:
        if "conda_env_yaml" in self.fix:
            passed.append("Conda environment name was correct ({})".format(expected_env_name))
            fixed.append(
                "Fixed Conda environment name: '{}' to '{}'".format(self.conda_config["name"], expected_env_name)
            )
            raw_environment_yml = raw_environment_yml.replace(self.conda_config["name"], expected_env_name)
        else:
            failed.append(
                "Conda environment name is incorrect ({}, should be {})".format(
                    self.conda_config["name"], expected_env_name
                )
            )
            could_fix = True
    else:
        passed.append("Conda environment name was correct ({})".format(expected_env_name))

    # Check conda dependency list
    conda_deps = self.conda_config.get("dependencies", [])
    if len(conda_deps) > 0:
        conda_progress = self.progress_bar.add_task(
            "Checking Conda packages", total=len(conda_deps), test_name=conda_deps[0]
        )
    for idx, dep in enumerate(conda_deps):
        self.progress_bar.update(conda_progress, advance=1, test_name=dep)
        if isinstance(dep, str):
            # Check that each dependency has a version number
            try:
                assert dep.count("=") in [1, 2]
            except AssertionError:
                failed.append("Conda dep did not have pinned version number: `{}`".format(dep))
            else:
                passed.append("Conda dep had pinned version number: `{}`".format(dep))

                try:
                    depname, depver = dep.split("=")[:2]
                    self.conda_package_info[dep] = anaconda_package(
                        dep, dep_channels=self.conda_config.get("channels", [])
                    )
                except LookupError as e:
                    warned.append(e)
                except ValueError as e:
                    failed.append(e)
                else:
                    # Check that required version is available at all
                    if depver not in self.conda_package_info[dep].get("versions"):
                        failed.append("Conda dep had unknown version: {}".format(dep))
                        continue  # No need to test for latest version, continue linting
                    # Check version is latest available
                    last_ver = self.conda_package_info[dep].get("latest_version")
                    if last_ver is not None and last_ver != depver:
                        if "conda_env_yaml" in self.fix:
                            passed.append("Conda package is the latest available: `{}`".format(dep))
                            fixed.append("Conda package updated: '{}' to '{}'".format(dep, last_ver))
                            raw_environment_yml = raw_environment_yml.replace(dep, f"{depname}={last_ver}")
                        else:
                            warned.append("Conda dep outdated: `{}`, `{}` available".format(dep, last_ver))
                            could_fix = True
                    else:
                        passed.append("Conda package is the latest available: `{}`".format(dep))

        elif isinstance(dep, dict):
            pip_deps = dep.get("pip", [])
            if len(pip_deps) > 0:
                pip_progress = self.progress_bar.add_task(
                    "Checking PyPI packages", total=len(pip_deps), test_name=pip_deps[0]
                )
            for pip_idx, pip_dep in enumerate(pip_deps):
                self.progress_bar.update(pip_progress, advance=1, test_name=pip_dep)
                # Check that each pip dependency has a version number
                try:
                    assert pip_dep.count("=") == 2
                except AssertionError:
                    failed.append("Pip dependency did not have pinned version number: {}".format(pip_dep))
                else:
                    passed.append("Pip dependency had pinned version number: {}".format(pip_dep))

                    try:
                        pip_depname, pip_depver = pip_dep.split("==", 1)
                        self.conda_package_info[pip_dep] = nf_core.utils.pip_package(pip_dep)
                    except LookupError as e:
                        warned.append(e)
                    except ValueError as e:
                        failed.append(e)
                    else:
                        # Check, if PyPI package version is available at all
                        if pip_depver not in self.conda_package_info[pip_dep].get("releases").keys():
                            failed.append("PyPI package had an unknown version: {}".format(pip_depver))
                            continue  # No need to test latest version, if not available
                        pip_last_ver = self.conda_package_info[pip_dep].get("info").get("version")
                        if pip_last_ver is not None and pip_last_ver != pip_depver:
                            if "conda_env_yaml" in self.fix:
                                passed.append("PyPI package is latest available: {}".format(pip_depver))
                                fixed.append("PyPI package updated: '{}' to '{}'".format(pip_depname, pip_last_ver))
                                raw_environment_yml = raw_environment_yml.replace(pip_depver, pip_last_ver)
                            else:
                                warned.append(
                                    "PyPI package is not latest available: {}, {} available".format(
                                        pip_depver, pip_last_ver
                                    )
                                )
                                could_fix = True
                        else:
                            passed.append("PyPI package is latest available: {}".format(pip_depver))
            self.progress_bar.update(pip_progress, visible=False)
    self.progress_bar.update(conda_progress, visible=False)

    # NB: It would be a lot easier to just do a yaml.dump on the dictionary we have,
    # but this discards all formatting and comments which is a pain.
    if "conda_env_yaml" in self.fix and len(fixed) > 0:
        with open(env_path, "w") as fh:
            fh.write(raw_environment_yml)

    return {"passed": passed, "warned": warned, "failed": failed, "fixed": fixed, "could_fix": could_fix}
