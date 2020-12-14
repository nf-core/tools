#!/usr/bin/env python

import logging
import os
import requests
import nf_core.utils

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

    if os.path.join(self.wf_path, "environment.yml") not in self.files:
        return {"ignored": ["No `environment.yml` file found - skipping conda_env_yaml test"]}

    # Check that the environment name matches the pipeline name
    pipeline_version = self.nf_config.get("manifest.version", "").strip(" '\"")
    expected_env_name = "nf-core-{}-{}".format(self.pipeline_name.lower(), pipeline_version)
    if self.conda_config["name"] != expected_env_name:
        failed.append(
            "Conda environment name is incorrect ({}, should be {})".format(
                self.conda_config["name"], expected_env_name
            )
        )
    else:
        passed.append("Conda environment name was correct ({})".format(expected_env_name))

    # Check conda dependency list
    for dep in self.conda_config.get("dependencies", []):
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
                    self.conda_package_info[dep] = _anaconda_package(self.conda_config, dep)
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
                        warned.append("Conda dep outdated: `{}`, `{}` available".format(dep, last_ver))
                    else:
                        passed.append("Conda package is the latest available: `{}`".format(dep))

        elif isinstance(dep, dict):
            for pip_dep in dep.get("pip", []):
                # Check that each pip dependency has a version number
                try:
                    assert pip_dep.count("=") == 2
                except AssertionError:
                    failed.append("Pip dependency did not have pinned version number: {}".format(pip_dep))
                else:
                    passed.append("Pip dependency had pinned version number: {}".format(pip_dep))

                    try:
                        pip_depname, pip_depver = pip_dep.split("==", 1)
                        self.conda_package_info[dep] = _pip_package(pip_dep)
                    except LookupError as e:
                        warned.append(e)
                    except ValueError as e:
                        failed.append(e)
                    else:
                        # Check, if PyPi package version is available at all
                        if pip_depver not in self.conda_package_info[pip_dep].get("releases").keys():
                            failed.append("PyPi package had an unknown version: {}".format(pip_depver))
                            continue  # No need to test latest version, if not available
                        last_ver = self.conda_package_info[pip_dep].get("info").get("version")
                        if last_ver is not None and last_ver != pip_depver:
                            warned.append(
                                "PyPi package is not latest available: {}, {} available".format(pip_depver, last_ver)
                            )
                        else:
                            passed.append("PyPi package is latest available: {}".format(pip_depver))

    return {"passed": passed, "warned": warned, "failed": failed}


def _anaconda_package(conda_config, dep):
    """Query conda package information.

    Sends a HTTP GET request to the Anaconda remote API.

    Args:
        dep (str): A conda package name.

    Raises:
        A LookupError, if the connection fails or times out or gives an unexpected status code
        A ValueError, if the package name can not be found (404)
    """

    # Check if each dependency is the latest available version
    depname, depver = dep.split("=", 1)
    dep_channels = conda_config.get("channels", [])
    # 'defaults' isn't actually a channel name. See https://docs.anaconda.com/anaconda/user-guide/tasks/using-repositories/
    if "defaults" in dep_channels:
        dep_channels.remove("defaults")
        dep_channels.extend(["main", "anaconda", "r", "free", "archive", "anaconda-extras"])
    if "::" in depname:
        dep_channels = [depname.split("::")[0]]
        depname = depname.split("::")[1]
    for ch in dep_channels:
        anaconda_api_url = "https://api.anaconda.org/package/{}/{}".format(ch, depname)
        try:
            response = requests.get(anaconda_api_url, timeout=10)
        except (requests.exceptions.Timeout):
            raise LookupError("Anaconda API timed out: {}".format(anaconda_api_url))
        except (requests.exceptions.ConnectionError):
            raise LookupError("Could not connect to Anaconda API")
        else:
            if response.status_code == 200:
                return response.json()
            elif response.status_code != 404:
                raise LookupError(
                    "Anaconda API returned unexpected response code `{}` for: {}\n{}".format(
                        response.status_code, anaconda_api_url, response
                    )
                )
            elif response.status_code == 404:
                log.debug("Could not find `{}` in conda channel `{}`".format(dep, ch))
    else:
        # We have looped through each channel and had a 404 response code on everything
        raise ValueError(
            "Could not find Conda dependency using the Anaconda API: `{}` (<{}>)".format(dep, anaconda_api_url)
        )


def _pip_package(dep):
    """Query PyPi package information.

    Sends a HTTP GET request to the PyPi remote API.

    Args:
        dep (str): A PyPi package name.

    Raises:
        A LookupError, if the connection fails or times out
        A ValueError, if the package name can not be found
    """
    pip_depname, pip_depver = dep.split("=", 1)
    pip_api_url = "https://pypi.python.org/pypi/{}/json".format(pip_depname)
    try:
        response = requests.get(pip_api_url, timeout=10)
    except (requests.exceptions.Timeout):
        raise LookupError("PyPi API timed out: {}".format(pip_api_url))
    except (requests.exceptions.ConnectionError):
        raise LookupError("PyPi API Connection error: {}".format(pip_api_url))
    else:
        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError("Could not find pip dependency using the PyPi API: `{}`".format(dep))
