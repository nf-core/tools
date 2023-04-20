""" Tests covering the subworkflows commands
"""

import os
import shutil
import tempfile
import unittest

import responses

import nf_core.create
import nf_core.modules
import nf_core.subworkflows

from .utils import (
    GITLAB_SUBWORKFLOWS_BRANCH,
    GITLAB_SUBWORKFLOWS_ORG_PATH_BRANCH,
    GITLAB_URL,
    OLD_SUBWORKFLOWS_SHA,
)


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
        fh.writelines(["repository_type: modules", "\n", "org_path: nf-core", "\n"])

    # TODO Add a mock here
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
        self.pipeline_name = "mypipeline"
        self.pipeline_dir = os.path.join(self.tmp_dir, self.pipeline_name)
        nf_core.create.PipelineCreate(
            self.pipeline_name, "it is mine", "me", no_git=True, outdir=self.pipeline_dir, plain=True
        ).init_pipeline()

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

    from .subworkflows.create import (
        test_subworkflows_create_fail_exists,
        test_subworkflows_create_nfcore_modules,
        test_subworkflows_create_succeed,
    )
    from .subworkflows.create_test_yml import (
        test_subworkflows_create_test_yml_check_inputs,
        test_subworkflows_create_test_yml_entry_points,
        test_subworkflows_create_test_yml_get_md5,
        test_subworkflows_custom_yml_dumper,
        test_subworkflows_test_file_dict,
    )
    from .subworkflows.info import (
        test_subworkflows_info_in_modules_repo,
        test_subworkflows_info_local,
        test_subworkflows_info_remote,
        test_subworkflows_info_remote_gitlab,
    )
    from .subworkflows.install import (
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
    from .subworkflows.list import (
        test_subworkflows_install_and_list_subworkflows,
        test_subworkflows_install_gitlab_and_list_subworkflows,
        test_subworkflows_list_remote,
        test_subworkflows_list_remote_gitlab,
    )
    from .subworkflows.remove import (
        test_subworkflows_remove_included_subworkflow,
        test_subworkflows_remove_one_of_two_subworkflow,
        test_subworkflows_remove_subworkflow,
        test_subworkflows_remove_subworkflow_keep_installed_module,
    )
    from .subworkflows.subworkflows_test import (
        test_subworkflows_test_check_inputs,
        test_subworkflows_test_no_installed_subworkflows,
        test_subworkflows_test_no_name_no_prompts,
    )
    from .subworkflows.update import (
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
