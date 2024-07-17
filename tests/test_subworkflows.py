"""Tests covering the subworkflows commands"""

import json
import os
import shutil
import unittest
from pathlib import Path

import pytest

import nf_core.modules
import nf_core.pipelines.create.create
import nf_core.subworkflows

from .utils import (
    GITLAB_SUBWORKFLOWS_BRANCH,
    GITLAB_SUBWORKFLOWS_ORG_PATH_BRANCH,
    GITLAB_URL,
    OLD_SUBWORKFLOWS_SHA,
    create_tmp_pipeline,
)


def create_modules_repo_dummy(tmp_dir):
    """Create a dummy copy of the nf-core/modules repo"""

    root_dir = Path(tmp_dir, "modules")
    Path(root_dir, "modules").mkdir(parents=True, exist_ok=True)
    Path(root_dir, "subworkflows", "nf-core").mkdir(parents=True, exist_ok=True)
    Path(root_dir, "tests", "config").mkdir(parents=True, exist_ok=True)
    with open(Path(root_dir, ".nf-core.yml"), "w") as fh:
        fh.writelines(["repository_type: modules", "\n", "org_path: nf-core", "\n"])
    # TODO Add a mock here
    subworkflow_create = nf_core.subworkflows.SubworkflowCreate(root_dir, "test_subworkflow", "@author", True)
    subworkflow_create.create()

    # Add dummy content to main.nf.test.snap
    test_snap_path = Path(
        root_dir,
        "subworkflows",
        "nf-core",
        "test_subworkflow",
        "tests",
        "main.nf.test.snap",
    )
    test_snap_path.parent.mkdir(parents=True, exist_ok=True)
    with open(test_snap_path, "w") as fh:
        json.dump(
            {
                "my test": {
                    "content": [
                        {
                            "0": [],
                            "versions": {},
                        }
                    ]
                }
            },
            fh,
            indent=4,
        )

    return root_dir


class TestSubworkflows(unittest.TestCase):
    """Class for subworkflows tests"""

    def setUp(self):
        """Create a new PipelineStructure and Launch objects"""
        self.component_type = "subworkflows"

        # Set up the pipeline structure
        self.tmp_dir, self.template_dir, self.pipeline_name, self.pipeline_dir = create_tmp_pipeline()

        # Set up the nf-core/modules repo dummy
        self.nfcore_modules = create_modules_repo_dummy(self.tmp_dir)

        # Set up install objects
        self.subworkflow_install = nf_core.subworkflows.SubworkflowInstall(self.pipeline_dir, prompt=False, force=False)
        self.subworkflow_install_gitlab = nf_core.subworkflows.SubworkflowInstall(
            self.pipeline_dir,
            prompt=False,
            force=False,
            remote_url=GITLAB_URL,
            branch=GITLAB_SUBWORKFLOWS_BRANCH,
        )
        self.subworkflow_install_gitlab_same_org_path = nf_core.subworkflows.SubworkflowInstall(
            self.pipeline_dir,
            prompt=False,
            force=False,
            remote_url=GITLAB_URL,
            branch=GITLAB_SUBWORKFLOWS_ORG_PATH_BRANCH,
        )
        self.subworkflow_install_old = nf_core.subworkflows.SubworkflowInstall(
            self.pipeline_dir,
            prompt=False,
            force=False,
            sha=OLD_SUBWORKFLOWS_SHA,
        )
        self.subworkflow_install_module_change = nf_core.subworkflows.SubworkflowInstall(
            self.pipeline_dir,
            prompt=False,
            force=False,
            sha="8c343b3c8a0925949783dc547666007c245c235b",
        )
        self.mods_install = nf_core.modules.ModuleInstall(self.pipeline_dir, prompt=False, force=True)

        # Set up remove objects
        self.subworkflow_remove = nf_core.subworkflows.SubworkflowRemove(self.pipeline_dir)

    def tearDown(self):
        """Clean up temporary files and folders"""

        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    @pytest.fixture(autouse=True)
    def _use_caplog(self, caplog):
        self.caplog = caplog

    # ################################################
    # # Test of the individual subworkflow commands. #
    # ################################################

    # from .subworkflows.list import (  # type: ignore[misc]
    #     test_subworkflows_install_and_list_subworkflows,
    #     test_subworkflows_install_gitlab_and_list_subworkflows,
    #     test_subworkflows_list_remote,
    #     test_subworkflows_list_remote_gitlab,
    # )
    # from .subworkflows.remove import (  # type: ignore[misc]
    #     test_subworkflows_remove_included_subworkflow,
    #     test_subworkflows_remove_one_of_two_subworkflow,
    #     test_subworkflows_remove_subworkflow,
    #     test_subworkflows_remove_subworkflow_keep_installed_module,
    # )
    # from .subworkflows.update import (  # type: ignore[misc]
    #     test_install_and_update,
    #     test_install_at_hash_and_update,
    #     test_install_at_hash_and_update_and_save_diff_limit_output,
    #     test_install_at_hash_and_update_and_save_diff_to_file,
    #     test_install_at_hash_and_update_limit_output,
    #     test_update_all,
    #     test_update_all_linked_components_from_subworkflow,
    #     test_update_all_subworkflows_from_module,
    #     test_update_change_of_included_modules,
    #     test_update_with_config_dont_update,
    #     test_update_with_config_fix_all,
    #     test_update_with_config_fixed_version,
    #     test_update_with_config_no_updates,
    # )
