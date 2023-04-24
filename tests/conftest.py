import os
import re

import pytest

import nf_core.modules

from .utils import (
    GITLAB_BRANCH_TEST_BRANCH,
    GITLAB_BRANCH_TEST_OLD_SHA,
    GITLAB_DEFAULT_BRANCH,
    GITLAB_URL,
    OLD_TRIMGALORE_BRANCH,
    OLD_TRIMGALORE_SHA,
)


@pytest.fixture
def tmp_dir(tmpdir):
    return tmpdir


@pytest.fixture
def pipeline_dir(tmp_dir):
    pipeline_dir = os.path.join(tmp_dir, "mypipeline")
    nf_core.create.PipelineCreate(
        "mypipeline", "it is mine", "me", no_git=True, outdir=pipeline_dir, plain=True
    ).init_pipeline()
    return pipeline_dir


@pytest.fixture
def modules_repo_dummy(tmp_dir):
    """Create a dummy copy of the nf-core/modules repo"""

    root_dir = os.path.join(tmp_dir, "modules")
    os.makedirs(os.path.join(root_dir, "modules", "nf-core"))
    os.makedirs(os.path.join(root_dir, "tests", "modules", "nf-core"))
    os.makedirs(os.path.join(root_dir, "tests", "config"))
    with open(os.path.join(root_dir, "tests", "config", "pytest_modules.yml"), "w") as fh:
        fh.writelines(["test:", "\n  - modules/test/**", "\n  - tests/modules/test/**"])
    with open(os.path.join(root_dir, ".nf-core.yml"), "w") as fh:
        fh.writelines(["repository_type: modules", "\n", "org_path: nf-core", "\n"])

    # mock biocontainers and anaconda response
    module_create = nf_core.modules.ModuleCreate(root_dir, "bpipe/test", "@author", "process_single", False, False)
    module_create.create()

    return root_dir


@pytest.fixture
def local_modules_repo(modules_repo_dummy, tmp_dir, pipeline_dir):
    """Create a new PipelineSchema and Launch objects"""
    component_type = "modules"

    # Set up the schema
    root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    template_dir = os.path.join(root_repo_dir, "nf_core", "pipeline-template")
    # Set up install objects
    mods_install = nf_core.modules.ModuleInstall(pipeline_dir, prompt=False, force=True)
    mods_install_old = nf_core.modules.ModuleInstall(
        pipeline_dir,
        prompt=False,
        force=False,
        sha=OLD_TRIMGALORE_SHA,
        remote_url=GITLAB_URL,
        branch=OLD_TRIMGALORE_BRANCH,
    )
    mods_install_trimgalore = nf_core.modules.ModuleInstall(
        pipeline_dir,
        prompt=False,
        force=True,
        remote_url=GITLAB_URL,
        branch=OLD_TRIMGALORE_BRANCH,
    )
    mods_install_gitlab = nf_core.modules.ModuleInstall(
        pipeline_dir,
        prompt=False,
        force=True,
        remote_url=GITLAB_URL,
        branch=GITLAB_DEFAULT_BRANCH,
    )
    mods_install_gitlab_old = nf_core.modules.ModuleInstall(
        pipeline_dir,
        prompt=False,
        force=True,
        remote_url=GITLAB_URL,
        branch=GITLAB_BRANCH_TEST_BRANCH,
        sha=GITLAB_BRANCH_TEST_OLD_SHA,
    )

    # Set up remove objects
    mods_remove = nf_core.modules.ModuleRemove(pipeline_dir)
    mods_remove_gitlab = nf_core.modules.ModuleRemove(
        pipeline_dir,
        remote_url=GITLAB_URL,
        branch=GITLAB_DEFAULT_BRANCH,
    )

    # Set up the nf-core/modules repo dummy
    nfcore_modules = modules_repo_dummy

    return nfcore_modules
