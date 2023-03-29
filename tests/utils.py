"""
Helper functions for tests
"""

import functools
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import responses

OLD_TRIMGALORE_SHA = "06348dffce2a732fc9e656bdc5c64c3e02d302cb"
OLD_TRIMGALORE_BRANCH = "mimic-old-trimgalore"
GITLAB_URL = "https://gitlab.com/nf-core/modules-test.git"
GITLAB_REPO = "nf-core"
GITLAB_DEFAULT_BRANCH = "main"
GITLAB_SUBWORKFLOWS_BRANCH = "subworkflows"
OLD_SUBWORKFLOWS_SHA = "f3c078809a2513f1c95de14f6633fe1f03572fdb"
# Branch test stuff
GITLAB_BRANCH_TEST_BRANCH = "branch-tester"
GITLAB_BRANCH_TEST_OLD_SHA = "bce3f17980b8d1beae5e917cfd3c65c0c69e04b5"
GITLAB_BRANCH_TEST_NEW_SHA = "2f5f180f6e705bb81d6e7742dc2f24bf4a0c721e"


def with_temporary_folder(func):
    """
    Call the decorated function under the tempfile.TemporaryDirectory
    context manager. Pass the temporary directory name to the decorated
    function
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with tempfile.TemporaryDirectory() as tmpdirname:
            return func(*args, tmpdirname, **kwargs)

    return wrapper


def with_temporary_file(func):
    """
    Call the decorated function under the tempfile.NamedTemporaryFile
    context manager. Pass the opened file handle to the decorated function
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with tempfile.NamedTemporaryFile() as tmpfile:
            return func(*args, tmpfile, **kwargs)

    return wrapper


@contextmanager
def set_wd(path: Path):
    """Sets the working directory for this context.

    Arguments
    ---------

    path : Path
        Path to the working directory to be used iside this context.
    """
    start_wd = Path().absolute()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(start_wd)


def mock_anaconda_api_calls(rsps: responses.RequestsMock, module, version):
    """Mock anaconda api calls for module"""
    anaconda_api_url = f"https://api.anaconda.org/package/bioconda/{module}"
    anaconda_mock = {
        "latest_version": version.split("--")[0],
        "summary": "",
        "doc_url": "",
        "dev_url": "",
        "files": [{"version": version.split("--")[0]}],
        "license": "",
    }
    rsps.get(anaconda_api_url, json=anaconda_mock, status=200)


def mock_biocontainers_api_calls(rsps: responses.RequestsMock, module, version):
    """Mock biocontainers api calls for module"""
    biocontainers_api_url = (
        f"https://api.biocontainers.pro/ga4gh/trs/v2/tools/{module}/versions/{module}-{version.split('--')[0]}"
    )
    biocontainers_mock = {
        "images": [
            {
                "image_type": "Singularity",
                "image_name": f"https://depot.galaxyproject.org/singularity/{module}:{version}",
                "updated": "2021-09-04T00:00:00Z",
            },
            {
                "image_type": "Docker",
                "image_name": f"quay.io/biocontainers/{module}:{version}",
                "updated": "2021-09-04T00:00:00Z",
            },
        ],
    }
    rsps.get(biocontainers_api_url, json=biocontainers_mock, status=200)
