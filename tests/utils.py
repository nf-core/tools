"""
Helper functions for tests
"""

import functools
import os
import tempfile
from typing import Any, Callable, Tuple

import responses

import nf_core.create
import nf_core.modules

OLD_TRIMGALORE_SHA = "9b7a3bdefeaad5d42324aa7dd50f87bea1b04386"
OLD_TRIMGALORE_BRANCH = "mimic-old-trimgalore"
GITLAB_URL = "https://gitlab.com/nf-core/modules-test.git"
GITLAB_REPO = "nf-core-test"
GITLAB_DEFAULT_BRANCH = "main"
GITLAB_SUBWORKFLOWS_BRANCH = "subworkflows"
GITLAB_SUBWORKFLOWS_ORG_PATH_BRANCH = "subworkflows-org-path"
OLD_SUBWORKFLOWS_SHA = "f3c078809a2513f1c95de14f6633fe1f03572fdb"
# Branch test stuff
GITLAB_BRANCH_TEST_BRANCH = "branch-tester"
GITLAB_BRANCH_ORG_PATH_BRANCH = "org-path"
GITLAB_BRANCH_TEST_OLD_SHA = "e772abc22c1ff26afdf377845c323172fb3c19ca"
GITLAB_BRANCH_TEST_NEW_SHA = "7d73e21f30041297ea44367f2b4fd4e045c0b991"
GITLAB_NFTEST_BRANCH = "nf-test-tests-self-hosted-runners"


def with_temporary_folder(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Call the decorated function under the tempfile.TemporaryDirectory
    context manager. Pass the temporary directory name to the decorated
    function
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with tempfile.TemporaryDirectory() as tmpdirname:
            return func(*args, tmpdirname, **kwargs)

    return wrapper


def with_temporary_file(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Call the decorated function under the tempfile.NamedTemporaryFile
    context manager. Pass the opened file handle to the decorated function
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with tempfile.NamedTemporaryFile() as tmpfile:
            return func(*args, tmpfile, **kwargs)

    return wrapper


def mock_anaconda_api_calls(rsps: responses.RequestsMock, module: str, version: str) -> None:
    """Mock anaconda api calls for module"""
    anaconda_api_url = f"https://api.anaconda.org/package/bioconda/{module}"
    anaconda_mock = {
        "latest_version": version.split("--")[0],
        "summary": "",
        "doc_url": "http://test",
        "dev_url": "http://test",
        "files": [{"version": version.split("--")[0]}],
        "license": "MIT",
    }
    rsps.get(anaconda_api_url, json=anaconda_mock, status=200)


def mock_biocontainers_api_calls(rsps: responses.RequestsMock, module: str, version: str) -> None:
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
                "image_name": f"biocontainers/{module}:{version}",
                "updated": "2021-09-04T00:00:00Z",
            },
        ],
    }
    rsps.get(biocontainers_api_url, json=biocontainers_mock, status=200)


def create_tmp_pipeline() -> Tuple[str, str, str, str]:
    """Create a new Pipeline for testing"""

    tmp_dir = tempfile.mkdtemp()
    root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    template_dir = os.path.join(root_repo_dir, "nf_core", "pipeline-template")
    pipeline_name = "mypipeline"
    pipeline_dir = os.path.join(tmp_dir, pipeline_name)

    nf_core.create.PipelineCreate(
        pipeline_name, "it is mine", "me", no_git=True, outdir=pipeline_dir, plain=True
    ).init_pipeline()

    # return values to instance variables for later use in test methods
    return tmp_dir, template_dir, pipeline_name, pipeline_dir
