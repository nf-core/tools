#!/usr/bin/env python
""" Tests covering the modules commands
"""

from nf_core.modules import create
import nf_core.modules

import os
import shutil
import tempfile
import unittest
import pytest
from rich.console import Console


def create_modules_repo_dummy():
    """Create a dummy copy of the nf-core/modules repo"""
    root_dir = tempfile.mkdtemp()
    os.mkdir(os.path.join(root_dir, "software"))
    os.makedirs(os.path.join(root_dir, "tests", "software"))
    os.makedirs(os.path.join(root_dir, "tests", "config"))
    with open(os.path.join(root_dir, "tests", "config", "pytest_software.yml"), "w") as fh:
        fh.writelines(["test:", "\n  - software/test/**", "\n  - tests/software/test/**"])

    module_create = nf_core.modules.ModuleCreate(root_dir, "star/align", "@author", "process_medium", False, False)
    module_create.create()

    return root_dir


class TestModules(unittest.TestCase):
    """Class for modules tests"""

    def setUp(self):
        """Create a new PipelineSchema and Launch objects"""
        # Set up the schema
        root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.template_dir = os.path.join(root_repo_dir, "nf_core", "pipeline-template")
        self.pipeline_dir = os.path.join(tempfile.mkdtemp(), "mypipeline")
        shutil.copytree(self.template_dir, self.pipeline_dir)
        self.mods = nf_core.modules.PipelineModules()
        self.mods.pipeline_dir = self.pipeline_dir
        self.mods_alt = nf_core.modules.PipelineModules()
        self.mods_alt.pipeline_dir = self.pipeline_dir
        self.mods_alt.modules_repo = nf_core.modules.ModulesRepo(repo="ewels/nf-core-modules", branch="master")

        # Set up the nf-core/modules repo dummy
        self.nfcore_modules = create_modules_repo_dummy()

    def test_modulesrepo_class(self):
        """Initialise a modules repo object"""
        modrepo = nf_core.modules.ModulesRepo()
        assert modrepo.name == "nf-core/modules"
        assert modrepo.branch == "master"

    def test_modules_list(self):
        """Test listing available modules"""
        self.mods.pipeline_dir = None
        listed_mods = self.mods.list_modules()
        console = Console(record=True)
        console.print(listed_mods)
        output = console.export_text()
        assert "fastqc" in output

    def test_modules_install_nopipeline(self):
        """Test installing a module - no pipeline given"""
        self.mods.pipeline_dir = None
        assert self.mods.install("foo") is False

    def test_modules_install_emptypipeline(self):
        """Test installing a module - empty dir given"""
        self.mods.pipeline_dir = tempfile.mkdtemp()
        with pytest.raises(UserWarning) as excinfo:
            self.mods.install("foo")
        assert "Could not find a 'main.nf' or 'nextflow.config' file" in str(excinfo.value)

    def test_modules_install_nomodule(self):
        """Test installing a module - unrecognised module given"""
        assert self.mods.install("foo") is False

    def test_modules_install_fastqc(self):
        """Test installing a module - FastQC"""
        assert self.mods.install("fastqc") is not False
        module_path = os.path.join(self.mods.pipeline_dir, "modules", "nf-core", "software", "fastqc")
        assert os.path.exists(module_path)

    def test_modules_install_fastqc_alternative_source(self):
        """Test installing a module from a different source repository - FastQC"""
        assert self.mods_alt.install("fastqc") is not False
        module_path = os.path.join(self.mods.pipeline_dir, "modules", "external", "fastqc")
        assert os.path.exists(module_path)

    def test_modules_install_fastqc_twice(self):
        """Test installing a module - FastQC already there"""
        self.mods.install("fastqc")
        assert self.mods.install("fastqc") is False

    def test_modules_remove_fastqc(self):
        """Test removing FastQC module after installing it"""
        self.mods.install("fastqc")
        module_path = os.path.join(self.mods.pipeline_dir, "modules", "nf-core", "software", "fastqc")
        assert self.mods.remove("fastqc")
        assert os.path.exists(module_path) is False

    def test_modules_remove_fastqc_alternative_source(self):
        """Test removing FastQC module after installing it from an alternative source"""
        self.mods_alt.install("fastqc")
        module_path = os.path.join(self.mods.pipeline_dir, "modules", "external", "fastqc")
        assert self.mods_alt.remove("fastqc")
        assert os.path.exists(module_path) is False

    def test_modules_remove_fastqc_uninstalled(self):
        """Test removing FastQC module without installing it"""
        assert self.mods.remove("fastqc") is False

    def test_modules_lint_fastqc(self):
        """Test linting the fastqc module"""
        self.mods.install("fastqc")
        module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir)
        module_lint.lint(print_results=False, all_modules=True)
        assert len(module_lint.passed) == 20
        assert len(module_lint.warned) == 0
        assert len(module_lint.failed) == 0

    def test_modules_lint_empty(self):
        """Test linting a pipeline with no modules installed"""
        module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir)
        module_lint.lint(print_results=False, all_modules=True)
        assert len(module_lint.passed) == 0
        assert len(module_lint.warned) == 0
        assert len(module_lint.failed) == 0

    def test_modules_lint_new_modules(self):
        """lint all modules in nf-core/modules repo clone"""
        module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
        module_lint.lint(print_results=True, all_modules=True)
        assert len(module_lint.passed) == 20
        assert len(module_lint.warned) == 23
        assert len(module_lint.failed) == 0

    def test_modules_create_succeed(self):
        """Succeed at creating the FastQC module"""
        module_create = nf_core.modules.ModuleCreate(self.pipeline_dir, "fastqc", "@author", "process_low", True, True)
        module_create.create()
        assert os.path.exists(os.path.join(self.pipeline_dir, "modules", "local", "fastqc.nf"))

    def test_modules_create_fail_exists(self):
        """Fail at creating the same module twice"""
        module_create = nf_core.modules.ModuleCreate(
            self.pipeline_dir, "fastqc", "@author", "process_low", False, False
        )
        module_create.create()
        with pytest.raises(UserWarning) as excinfo:
            module_create.create()
        assert "Module file exists already" in str(excinfo.value)

    def test_modules_custom_yml_dumper(self):
        """Try to create a yml file with the custom yml dumper"""
        out_dir = tempfile.mkdtemp()
        yml_output_path = os.path.join(out_dir, "test.yml")
        meta_builder = nf_core.modules.ModulesTestYmlBuilder("test/tool", False, "./", False, True)
        meta_builder.test_yml_output_path = yml_output_path
        meta_builder.tests = [{"testname": "myname"}]
        meta_builder.print_test_yml()
        assert os.path.isfile(yml_output_path)

    def test_modules_test_file_dict(self):
        """Creat dict of test files and create md5 sums"""
        test_file_dir = tempfile.mkdtemp()
        meta_builder = nf_core.modules.ModulesTestYmlBuilder("test/tool", False, "./", False, True)
        with open(os.path.join(test_file_dir, "test_file.txt"), "w") as fh:
            fh.write("this line is just for testing")
        test_files = meta_builder.create_test_file_dict(test_file_dir)
        assert len(test_files) == 1
        assert test_files[0]["md5sum"] == "2191e06b28b5ba82378bcc0672d01786"

    def test_modules_create_test_yml_get_md5(self):
        """Get md5 sums from a dummy output"""
        test_file_dir = tempfile.mkdtemp()
        meta_builder = nf_core.modules.ModulesTestYmlBuilder("test/tool", False, "./", False, True)
        with open(os.path.join(test_file_dir, "test_file.txt"), "w") as fh:
            fh.write("this line is just for testing")
        test_files = meta_builder.get_md5_sums(
            entry_point="dummy", command="dummy", results_dir=test_file_dir, results_dir_repeat=test_file_dir
        )
        assert test_files[0]["md5sum"] == "2191e06b28b5ba82378bcc0672d01786"

    def test_modules_create_test_yml_entry_points(self):
        """Test extracting test entry points from a main.nf file"""
        meta_builder = nf_core.modules.ModulesTestYmlBuilder("star/align", False, "./", False, True)
        meta_builder.module_test_main = os.path.join(
            self.nfcore_modules, "tests", "software", "star", "align", "main.nf"
        )
        meta_builder.scrape_workflow_entry_points()
        assert meta_builder.entry_points[0] == "test_star_align"

    def test_modules_create_test_yml_check_inputs(self):
        """Test the check_inputs() function - raise UserWarning because test.yml exists"""
        cwd = os.getcwd()
        os.chdir(self.nfcore_modules)
        meta_builder = nf_core.modules.ModulesTestYmlBuilder("star/align", False, "./", False, True)
        meta_builder.module_test_main = os.path.join(
            self.nfcore_modules, "tests", "software", "star", "align", "main.nf"
        )
        with pytest.raises(UserWarning) as excinfo:
            meta_builder.check_inputs()
        os.chdir(cwd)
        assert "Test YAML file already exists!" in str(excinfo.value)

    def test_modules_create_nfcore_modules(self):
        """Create a module in nf-core/modules clone"""
        module_create = nf_core.modules.ModuleCreate(
            self.nfcore_modules, "fastqc", "@author", "process_low", False, False
        )
        module_create.create()
        assert os.path.exists(os.path.join(self.nfcore_modules, "software", "fastqc", "main.nf"))
        assert os.path.exists(os.path.join(self.nfcore_modules, "tests", "software", "fastqc", "main.nf"))

    def test_modules_create_nfcore_modules_subtool(self):
        """Create a tool/subtool module in a nf-core/modules clone"""
        module_create = nf_core.modules.ModuleCreate(
            self.nfcore_modules, "star/index", "@author", "process_medium", False, False
        )
        module_create.create()
        assert os.path.exists(os.path.join(self.nfcore_modules, "software", "star", "index", "main.nf"))
        assert os.path.exists(os.path.join(self.nfcore_modules, "tests", "software", "star", "index", "main.nf"))
