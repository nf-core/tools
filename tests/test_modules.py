#!/usr/bin/env python
""" Tests covering the modules commands
"""

import nf_core.modules

import os
import shutil
import tempfile
import unittest


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
        shutil.copytree(self.template_dir, self.pipeline_dir)

        # Set up install objects
        print("Setting up install objects")
        self.mods_install = nf_core.modules.ModuleInstall(self.pipeline_dir, prompt=False, force=True)
        self.mods_install_alt = nf_core.modules.ModuleInstall(self.pipeline_dir, prompt=True, force=True)

        # Set up remove objects
        print("Setting up remove objects")
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
        assert modrepo.name == "nf-core/modules"
        assert modrepo.branch == "master"

    ############################################
    # Test of the individual modules commands. #
    ############################################

    from .modules.list import (
        test_modules_list_remote,
        test_modules_list_pipeline,
        test_modules_install_and_list_pipeline,
    )

    from .modules.install import (
        test_modules_install_nopipeline,
        test_modules_install_emptypipeline,
        test_modules_install_nomodule,
        test_modules_install_trimgalore,
        test_modules_install_trimgalore_twice,
    )

    from .modules.remove import (
        test_modules_remove_trimgalore,
        test_modules_remove_trimgalore_uninstalled,
    )

    from .modules.lint import test_modules_lint_trimgalore, test_modules_lint_empty, test_modules_lint_new_modules

    from .modules.create import (
        test_modules_create_succeed,
        test_modules_create_fail_exists,
        test_modules_create_nfcore_modules,
        test_modules_create_nfcore_modules_subtool,
    )

    from .modules.create_test_yml import (
        test_modules_custom_yml_dumper,
        test_modules_test_file_dict,
        test_modules_create_test_yml_get_md5,
        test_modules_create_test_yml_entry_points,
        test_modules_create_test_yml_check_inputs,
    )

    from .modules.bump_versions import (
        test_modules_bump_versions_single_module,
        test_modules_bump_versions_all_modules,
        test_modules_bump_versions_fail,
        test_modules_bump_versions_fail_unknown_version,
    )
