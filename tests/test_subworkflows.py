"""Tests covering the subworkflows commands"""

import json
import os
import shutil
import unittest
from pathlib import Path

import nf_core.create
import nf_core.modules
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
    test_snap_path = Path(root_dir, "subworkflows", "nf-core", "test_subworkflow", "tests", "main.nf.test.snap")
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
            self.pipeline_dir, prompt=False, force=False, remote_url=GITLAB_URL, branch=GITLAB_SUBWORKFLOWS_BRANCH
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

    ################################################
    # Test of the individual subworkflow commands. #
    ################################################

    from .subworkflows.create import (  # type: ignore[misc]
        test_subworkflows_create_fail_exists,
        test_subworkflows_create_nfcore_modules,
        test_subworkflows_create_succeed,
        test_subworkflows_migrate,
        test_subworkflows_migrate_no_delete,
    )
    from .subworkflows.info import (  # type: ignore[misc]
        test_subworkflows_info_in_modules_repo,
        test_subworkflows_info_local,
        test_subworkflows_info_remote,
        test_subworkflows_info_remote_gitlab,
    )
    from .subworkflows.install import (  # type: ignore[misc]
        test_subworkflow_install_nopipeline,
        test_subworkflows_install_alternate_remote,
        test_subworkflows_install_bam_sort_stats_samtools,
        test_subworkflows_install_bam_sort_stats_samtools_twice,
        test_subworkflows_install_different_branch_fail,
        test_subworkflows_install_emptypipeline,
        test_subworkflows_install_from_gitlab,
        test_subworkflows_install_nosubworkflow,
        test_subworkflows_install_tracking,
        test_subworkflows_install_tracking_added_already_installed,
        test_subworkflows_install_tracking_added_super_subworkflow,
    )
    from .subworkflows.lint import (  # type: ignore[misc]
        test_subworkflows_absent_version,
        test_subworkflows_empty_file_in_snapshot,
        test_subworkflows_empty_file_in_stub_snapshot,
        test_subworkflows_incorrect_tags_yml_key,
        test_subworkflows_incorrect_tags_yml_values,
        test_subworkflows_lint,
        test_subworkflows_lint_capitalization_fail,
        test_subworkflows_lint_empty,
        test_subworkflows_lint_gitlab_subworkflows,
        test_subworkflows_lint_include_multiple_alias,
        test_subworkflows_lint_less_than_two_modules_warning,
        test_subworkflows_lint_multiple_remotes,
        test_subworkflows_lint_new_subworkflow,
        test_subworkflows_lint_no_gitlab,
        test_subworkflows_lint_snapshot_file,
        test_subworkflows_lint_snapshot_file_missing_fail,
        test_subworkflows_lint_snapshot_file_not_needed,
        test_subworkflows_missing_tags_yml,
    )
    from .subworkflows.list import (  # type: ignore[misc]
        test_subworkflows_install_and_list_subworkflows,
        test_subworkflows_install_gitlab_and_list_subworkflows,
        test_subworkflows_list_remote,
        test_subworkflows_list_remote_gitlab,
    )
    from .subworkflows.remove import (  # type: ignore[misc]
        test_subworkflows_remove_included_subworkflow,
        test_subworkflows_remove_one_of_two_subworkflow,
        test_subworkflows_remove_subworkflow,
        test_subworkflows_remove_subworkflow_keep_installed_module,
    )
    from .subworkflows.update import (  # type: ignore[misc]
        test_install_and_update,
        test_install_at_hash_and_update,
        test_install_at_hash_and_update_and_save_diff_to_file,
        test_update_all,
        test_update_all_linked_components_from_subworkflow,
        test_update_all_subworkflows_from_module,
        test_update_change_of_included_modules,
        test_update_with_config_dont_update,
        test_update_with_config_fix_all,
        test_update_with_config_fixed_version,
        test_update_with_config_no_updates,
    )
