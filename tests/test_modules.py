"""Tests covering the modules commands"""

import json
import os
import shutil
import unittest
from pathlib import Path

import requests_cache
import responses
import yaml

import nf_core.create
import nf_core.modules

from .utils import (
    GITLAB_BRANCH_TEST_BRANCH,
    GITLAB_BRANCH_TEST_OLD_SHA,
    GITLAB_DEFAULT_BRANCH,
    GITLAB_URL,
    OLD_TRIMGALORE_BRANCH,
    OLD_TRIMGALORE_SHA,
    create_tmp_pipeline,
    mock_anaconda_api_calls,
    mock_biocontainers_api_calls,
)


def create_modules_repo_dummy(tmp_dir):
    """Create a dummy copy of the nf-core/modules repo"""

    root_dir = Path(tmp_dir, "modules")
    Path(root_dir, "modules", "nf-core").mkdir(parents=True)
    Path(root_dir, "tests", "modules", "nf-core").mkdir(parents=True)
    Path(root_dir, "tests", "config").mkdir(parents=True)
    with open(Path(root_dir, ".nf-core.yml"), "w") as fh:
        fh.writelines(["repository_type: modules", "\n", "org_path: nf-core", "\n"])
    # mock biocontainers and anaconda response
    with responses.RequestsMock() as rsps:
        mock_anaconda_api_calls(rsps, "bpipe", "0.9.11--hdfd78af_0")
        mock_biocontainers_api_calls(rsps, "bpipe", "0.9.11--hdfd78af_0")
        # bpipe is a valid package on bioconda that is very unlikely to ever be added to nf-core/modules
        module_create = nf_core.modules.ModuleCreate(root_dir, "bpipe/test", "@author", "process_single", False, False)
        with requests_cache.disabled():
            module_create.create()

    # Remove doi from meta.yml which makes lint fail
    meta_yml_path = Path(root_dir, "modules", "nf-core", "bpipe", "test", "meta.yml")

    with open(meta_yml_path) as fh:
        meta_yml = yaml.safe_load(fh)
    del meta_yml["tools"][0]["bpipe"]["doi"]
    with open(meta_yml_path, "w") as fh:
        yaml.dump(meta_yml, fh)
    # Add dummy content to main.nf.test.snap
    test_snap_path = Path(root_dir, "modules", "nf-core", "bpipe", "test", "tests", "main.nf.test.snap")

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

    # remove "TODO" statements from main.nf
    main_nf_path = Path(root_dir, "modules", "nf-core", "bpipe", "test", "main.nf")
    with open(main_nf_path) as fh:
        main_nf = fh.read()
    main_nf = main_nf.replace("TODO", "")
    with open(main_nf_path, "w") as fh:
        fh.write(main_nf)

    # remove "TODO" statements from main.nf.test
    main_nf_test_path = Path(root_dir, "modules", "nf-core", "bpipe", "test", "tests", "main.nf.test")
    with open(main_nf_test_path) as fh:
        main_nf_test = fh.read()
    main_nf_test = main_nf_test.replace("TODO", "")
    with open(main_nf_test_path, "w") as fh:
        fh.write(main_nf_test)

    return root_dir


class TestModules(unittest.TestCase):
    """Class for modules tests"""

    def setUp(self):
        """Create a new PipelineSchema and Launch objects"""
        self.component_type = "modules"

        # Set up the schema
        self.tmp_dir, self.template_dir, self.pipeline_name, self.pipeline_dir = create_tmp_pipeline()
        # Set up install objects
        self.mods_install = nf_core.modules.ModuleInstall(self.pipeline_dir, prompt=False, force=True)
        self.mods_install_old = nf_core.modules.ModuleInstall(
            self.pipeline_dir,
            prompt=False,
            force=False,
            sha=OLD_TRIMGALORE_SHA,
            remote_url=GITLAB_URL,
            branch=OLD_TRIMGALORE_BRANCH,
        )
        self.mods_install_trimgalore = nf_core.modules.ModuleInstall(
            self.pipeline_dir,
            prompt=False,
            force=False,
            remote_url=GITLAB_URL,
            branch=OLD_TRIMGALORE_BRANCH,
        )
        self.mods_install_gitlab = nf_core.modules.ModuleInstall(
            self.pipeline_dir,
            prompt=False,
            force=False,
            remote_url=GITLAB_URL,
            branch=GITLAB_DEFAULT_BRANCH,
        )
        self.mods_install_gitlab_old = nf_core.modules.ModuleInstall(
            self.pipeline_dir,
            prompt=False,
            force=False,
            remote_url=GITLAB_URL,
            branch=GITLAB_BRANCH_TEST_BRANCH,
            sha=GITLAB_BRANCH_TEST_OLD_SHA,
        )

        # Set up remove objects
        self.mods_remove = nf_core.modules.ModuleRemove(self.pipeline_dir)
        self.mods_remove_gitlab = nf_core.modules.ModuleRemove(
            self.pipeline_dir,
            remote_url=GITLAB_URL,
            branch=GITLAB_DEFAULT_BRANCH,
        )

        # Set up the nf-core/modules repo dummy
        self.nfcore_modules = create_modules_repo_dummy(self.tmp_dir)

    def tearDown(self):
        """Clean up temporary files and folders"""

        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def test_modulesrepo_class(self):
        """Initialise a modules repo object"""
        modrepo = nf_core.modules.ModulesRepo()
        assert modrepo.repo_path == "nf-core"
        assert modrepo.branch == "master"

    ############################################
    # Test of the individual modules commands. #
    ############################################

    from .modules.bump_versions import (  # type: ignore[misc]
        test_modules_bump_versions_all_modules,
        test_modules_bump_versions_fail,
        test_modules_bump_versions_fail_unknown_version,
        test_modules_bump_versions_single_module,
    )
    from .modules.create import (  # type: ignore[misc]
        test_modules_create_fail_exists,
        test_modules_create_nfcore_modules,
        test_modules_create_nfcore_modules_subtool,
        test_modules_create_succeed,
        test_modules_migrate,
        test_modules_migrate_no_delete,
        test_modules_migrate_symlink,
    )
    from .modules.info import (  # type: ignore[misc]
        test_modules_info_in_modules_repo,
        test_modules_info_local,
        test_modules_info_remote,
        test_modules_info_remote_gitlab,
    )
    from .modules.install import (  # type: ignore[misc]
        test_modules_install_alternate_remote,
        test_modules_install_different_branch_fail,
        test_modules_install_different_branch_succeed,
        test_modules_install_emptypipeline,
        test_modules_install_from_gitlab,
        test_modules_install_nomodule,
        test_modules_install_nopipeline,
        test_modules_install_tracking,
        test_modules_install_trimgalore,
        test_modules_install_trimgalore_twice,
    )
    from .modules.lint import (  # type: ignore[misc]
        test_modules_absent_version,
        test_modules_empty_file_in_snapshot,
        test_modules_empty_file_in_stub_snapshot,
        test_modules_environment_yml_file_doesnt_exists,
        test_modules_environment_yml_file_name_mismatch,
        test_modules_environment_yml_file_not_array,
        test_modules_environment_yml_file_sorted_correctly,
        test_modules_environment_yml_file_sorted_incorrectly,
        test_modules_incorrect_tags_yml_key,
        test_modules_incorrect_tags_yml_values,
        test_modules_lint_check_process_labels,
        test_modules_lint_check_url,
        test_modules_lint_empty,
        test_modules_lint_gitlab_modules,
        test_modules_lint_multiple_remotes,
        test_modules_lint_new_modules,
        test_modules_lint_no_gitlab,
        test_modules_lint_patched_modules,
        test_modules_lint_snapshot_file,
        test_modules_lint_snapshot_file_missing_fail,
        test_modules_lint_snapshot_file_not_needed,
        test_modules_lint_trimgalore,
        test_modules_meta_yml_incorrect_licence_field,
        test_modules_meta_yml_incorrect_name,
        test_modules_meta_yml_input_mismatch,
        test_modules_meta_yml_output_mismatch,
        test_modules_missing_required_tag,
        test_modules_missing_tags_yml,
        test_modules_missing_test_dir,
        test_modules_missing_test_main_nf,
        test_modules_unused_pytest_files,
        test_nftest_failing_linting,
    )
    from .modules.list import (  # type: ignore[misc]
        test_modules_install_and_list_pipeline,
        test_modules_install_gitlab_and_list_pipeline,
        test_modules_list_in_wrong_repo_fail,
        test_modules_list_local_json,
        test_modules_list_pipeline,
        test_modules_list_remote,
        test_modules_list_remote_gitlab,
        test_modules_list_remote_json,
        test_modules_list_with_keywords,
        test_modules_list_with_one_keyword,
        test_modules_list_with_unused_keyword,
    )
    from .modules.modules_json import (  # type: ignore[misc]
        test_get_modules_json,
        test_mod_json_create,
        test_mod_json_create_with_patch,
        test_mod_json_dump,
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
    from .modules.patch import (  # type: ignore[misc]
        test_create_patch_change,
        test_create_patch_no_change,
        test_create_patch_try_apply_failed,
        test_create_patch_try_apply_successful,
        test_create_patch_update_fail,
        test_create_patch_update_success,
        test_remove_patch,
    )
    from .modules.remove import (  # type: ignore[misc]
        test_modules_remove_multiqc_from_gitlab,
        test_modules_remove_trimgalore,
        test_modules_remove_trimgalore_uninstalled,
    )
    from .modules.update import (  # type: ignore[misc]
        test_install_and_update,
        test_install_at_hash_and_update,
        test_install_at_hash_and_update_and_save_diff_to_file,
        test_update_all,
        test_update_different_branch_mix_modules_branch_test,
        test_update_different_branch_mixed_modules_main,
        test_update_different_branch_single_module,
        test_update_module_with_extra_config_file,
        test_update_only_show_differences,
        test_update_only_show_differences_when_patch,
        test_update_with_config_dont_update,
        test_update_with_config_fix_all,
        test_update_with_config_fixed_version,
        test_update_with_config_no_updates,
    )
