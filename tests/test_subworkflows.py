""" Tests covering the subworkflows commands
"""

import os
import shutil
import tempfile
import unittest

import requests_mock

import nf_core.create
import nf_core.modules
import nf_core.subworkflows

from .utils import GITLAB_URL, mock_api_calls


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
        mock_api_calls(mock, "bpipe", "0.9.11")
        # bpipe is a valid package on bioconda that is very unlikely to ever be added to nf-core/modules
        module_create = nf_core.modules.ModuleCreate(root_dir, "bpipe/test", "@author", "process_medium", False, False)
        module_create.create()

    return root_dir


class TestSubworkflows(unittest.TestCase):
    """Class for subworkflows tests"""

    def setUp(self):
        """Create a new PipelineStructure and Launch objects"""
        self.tmp_dir = tempfile.mkdtemp()

        # Set up the pipeline structure
        root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.template_dir = os.path.join(root_repo_dir, "nf_core", "pipeline-template")
        self.pipeline_dir = os.path.join(self.tmp_dir, "mypipeline")
        nf_core.create.PipelineCreate(
            "mypipeline", "it is mine", "me", no_git=True, outdir=self.pipeline_dir, plain=True
        ).init_pipeline()

        # Set up the nf-core/modules repo dummy
        self.nfcore_modules = create_modules_repo_dummy(self.tmp_dir)

    ############################################
    # Test of the individual modules commands. #
    ############################################

    from .subworkflows.create import (
        test_subworkflows_create_fail_exists,
        test_subworkflows_create_nfcore_modules,
        test_subworkflows_create_succeed,
    )
    from .subworkflows.subworkflows_test import (
        test_subworkflows_test_check_inputs,
        test_subworkflows_test_no_installed_subworkflows,
        test_subworkflows_test_no_name_no_prompts,
    )
