#!/usr/bin/env python
""" Tests covering the modules commands
"""

import os
import shutil
import tempfile
import unittest

import nf_core.create
import nf_core.modules

from .utils import GITLAB_URL, OLD_TRIMGALORE_SHA


def create_modules_repo_dummy(tmp_dir):
    """Create a dummy copy of the nf-core/modules repo"""

    root_dir = os.path.join(tmp_dir, "modules")
    os.makedirs(os.path.join(root_dir, "modules"))
    os.makedirs(os.path.join(root_dir, "tests", "modules"))
    os.makedirs(os.path.join(root_dir, "tests", "config"))
    with open(os.path.join(root_dir, "tests", "config", "pytest_modules.yml"), "w") as fh:
        fh.writelines(["test:", "\n  - modules/test/**", "\n  - tests/modules/test/**"])
    with open(os.path.join(root_dir, ".nf-core.yml"), "w") as fh:
        fh.writelines(["repository_type: modules", "\n"])

    # bpipe is a valid package on bioconda that is very unlikely to ever be added to nf-core/modules
    module_create = nf_core.modules.ModuleCreate(root_dir, "bpipe/test", "@author", "process_medium", False, False)
    module_create.create()

    return root_dir


class TestModules(unittest.TestCase):
    """Class for modules tests"""

    def setUp(self):
        """Create a new PipelineSchema and Launch objects"""
        self.tmp_dir = tempfile.mkdtemp()

        # Set up the schema
        root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.template_dir = os.path.join(root_repo_dir, "nf_core", "pipeline-template")
        self.pipeline_dir = os.path.join(self.tmp_dir, "mypipeline")
        nf_core.create.PipelineCreate(
            "mypipeline", "it is mine", "me", no_git=True, outdir=self.pipeline_dir, plain=True
        ).init_pipeline()
        # Set up install objects
        self.mods_install = nf_core.modules.ModuleInstall(self.pipeline_dir, prompt=False, force=True)
        self.mods_install_alt = nf_core.modules.ModuleInstall(self.pipeline_dir, prompt=True, force=True)
        self.mods_install_old = nf_core.modules.ModuleInstall(
            self.pipeline_dir, prompt=False, force=False, sha=OLD_TRIMGALORE_SHA
        )
        self.mods_install_gitlab = nf_core.modules.ModuleInstall(
            self.pipeline_dir, prompt=False, force=True, remote_url=GITLAB_URL
        )

        # Set up remove objects
        self.mods_remove = nf_core.modules.ModuleRemove(self.pipeline_dir)
        self.mods_remove_alt = nf_core.modules.ModuleRemove(self.pipeline_dir)

        # Set up the nf-core/modules repo dummy
        self.nfcore_modules = create_modules_repo_dummy(self.tmp_dir)

    def tearDown(self):
        """Clean up temporary files and folders"""

        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def test_modulesrepo_class(self):
        """Initialise a modules repo object"""
        modrepo = nf_core.modules.ModulesRepo()
        assert modrepo.fullname == "nf-core/modules"
        assert modrepo.branch == "master"

    ############################################
    # Test of the individual modules commands. #
    ############################################

    from .modules.bump_versions import (
        test_modules_bump_versions_all_modules,
        test_modules_bump_versions_fail,
        test_modules_bump_versions_fail_unknown_version,
        test_modules_bump_versions_single_module,
    )
    from .modules.create import (
        test_modules_create_fail_exists,
        test_modules_create_nfcore_modules,
        test_modules_create_nfcore_modules_subtool,
        test_modules_create_succeed,
    )
    from .modules.create_test_yml import (
        test_modules_create_test_yml_check_inputs,
        test_modules_create_test_yml_entry_points,
        test_modules_create_test_yml_get_md5,
        test_modules_custom_yml_dumper,
        test_modules_test_file_dict,
    )
    from .modules.install import (
        test_modules_install_different_branch_fail,
        test_modules_install_different_branch_succeed,
        test_modules_install_emptypipeline,
        test_modules_install_from_gitlab,
        test_modules_install_nomodule,
        test_modules_install_nopipeline,
        test_modules_install_trimgalore,
        test_modules_install_trimgalore_twice,
    )
    from .modules.lint import (
        test_modules_lint_empty,
        test_modules_lint_gitlab_modules,
        test_modules_lint_new_modules,
        test_modules_lint_no_gitlab,
        test_modules_lint_patched_modules,
        test_modules_lint_trimgalore,
    )
    from .modules.list import (
        test_modules_install_and_list_pipeline,
        test_modules_install_gitlab_and_list_pipeline,
        test_modules_list_pipeline,
        test_modules_list_remote,
        test_modules_list_remote_gitlab,
    )
    from .modules.module_test import (
        test_modules_test_check_inputs,
        test_modules_test_no_installed_modules,
        test_modules_test_no_name_no_prompts,
    )
    from .modules.modules_json import (
        test_get_modules_json,
        test_mod_json_create,
        test_mod_json_create_with_patch,
        test_mod_json_dump,
        test_mod_json_get_git_url,
        test_mod_json_get_module_version,
        test_mod_json_module_present,
        test_mod_json_repo_present,
        test_mod_json_up_to_date,
        test_mod_json_up_to_date_module_removed,
        test_mod_json_up_to_date_reinstall_fails,
        test_mod_json_update,
        test_mod_json_with_empty_modules_value,
        test_mod_json_with_missing_modules_entry,
    )
    from .modules.patch import (
        test_create_patch_change,
        test_create_patch_no_change,
        test_create_patch_try_apply_failed,
        test_create_patch_try_apply_successful,
        test_create_patch_update_fail,
        test_create_patch_update_success,
    )
    from .modules.remove import (
        test_modules_remove_trimgalore,
        test_modules_remove_trimgalore_uninstalled,
    )
    from .modules.update import (
        test_install_and_update,
        test_install_at_hash_and_update,
        test_install_at_hash_and_update_and_save_diff_to_file,
        test_update_all,
        test_update_different_branch_mix_modules_branch_test,
        test_update_different_branch_mixed_modules_main,
        test_update_different_branch_single_module,
        test_update_with_config_dont_update,
        test_update_with_config_fix_all,
        test_update_with_config_fixed_version,
        test_update_with_config_no_updates,
    )
