""" Tests covering the subworkflows commands
"""

import os
import tempfile
import unittest

import requests_mock

import nf_core.create
import nf_core.modules
import nf_core.subworkflows

from .utils import GITLAB_SUBWORKFLOWS_BRANCH, GITLAB_URL, mock_api_calls


def create_modules_repo_dummy(tmp_dir):
    """Create a dummy copy of the nf-core/modules repo"""

    root_dir = os.path.join(tmp_dir, "modules")
    os.makedirs(os.path.join(root_dir, "modules"))
    os.makedirs(os.path.join(root_dir, "subworkflows"))
    os.makedirs(os.path.join(root_dir, "subworkflows", "nf-core"))
    os.makedirs(os.path.join(root_dir, "tests", "modules"))
    os.makedirs(os.path.join(root_dir, "tests", "subworkflows"))
    os.makedirs(os.path.join(root_dir, "tests", "config"))
    with open(os.path.join(root_dir, "tests", "config", "pytest_modules.yml"), "w") as fh:
        fh.writelines(["test:", "\n  - modules/test/**", "\n  - tests/modules/test/**"])
    with open(os.path.join(root_dir, ".nf-core.yml"), "w") as fh:
        fh.writelines(["repository_type: modules", "\n"])

    with requests_mock.Mocker() as mock:
        subworkflow_create = nf_core.subworkflows.SubworkflowCreate(root_dir, "test_subworkflow", "@author", True)
        subworkflow_create.create()

    return root_dir


class TestSubworkflows(unittest.TestCase):
    """Class for subworkflows tests"""

    def setUp(self):
        """Create a new PipelineStructure and Launch objects"""
        self.tmp_dir = tempfile.mkdtemp()
        self.component_type = "subworkflows"

        # Set up the pipeline structure
        root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.template_dir = os.path.join(root_repo_dir, "nf_core", "pipeline-template")
        self.pipeline_dir = os.path.join(self.tmp_dir, "mypipeline")
        nf_core.create.PipelineCreate(
            "mypipeline", "it is mine", "me", no_git=True, outdir=self.pipeline_dir, plain=True
        ).init_pipeline()

        # Set up install objects
        self.subworkflow_install = nf_core.subworkflows.SubworkflowInstall(self.pipeline_dir, prompt=False, force=False)
        self.subworkflow_install_gitlab = nf_core.subworkflows.SubworkflowInstall(
            self.pipeline_dir, prompt=False, force=False, remote_url=GITLAB_URL, branch=GITLAB_SUBWORKFLOWS_BRANCH
        )

        # Set up the nf-core/modules repo dummy
        self.nfcore_modules = create_modules_repo_dummy(self.tmp_dir)

        # Set up install objects
        self.sw_install = nf_core.subworkflows.SubworkflowInstall(self.pipeline_dir, prompt=False, force=False)
        self.sw_install_gitlab = nf_core.subworkflows.SubworkflowInstall(
            self.pipeline_dir, prompt=False, force=False, remote_url=GITLAB_URL, branch=GITLAB_SUBWORKFLOWS_BRANCH
        )

    ############################################
    # Test of the individual modules commands. #
    ############################################

    from .subworkflows.create import (
        test_subworkflows_create_fail_exists,
        test_subworkflows_create_nfcore_modules,
        test_subworkflows_create_succeed,
    )
    from .subworkflows.install import (
        test_subworkflow_install_nopipeline,
        test_subworkflows_install_bam_sort_stats_samtools,
        test_subworkflows_install_bam_sort_stats_samtools_twice,
        test_subworkflows_install_different_branch_fail,
        test_subworkflows_install_emptypipeline,
        test_subworkflows_install_from_gitlab,
        test_subworkflows_install_nosubworkflow,
    )
    from .subworkflows.list import (
        test_subworkflows_install_and_list_subworkflows,
        test_subworkflows_install_gitlab_and_list_subworkflows,
        test_subworkflows_list_remote,
        test_subworkflows_list_remote_gitlab,
    )
    from .subworkflows.subworkflows_test import (
        test_subworkflows_test_check_inputs,
        test_subworkflows_test_no_installed_subworkflows,
        test_subworkflows_test_no_name_no_prompts,
    )
