#!/usr/bin/env python
""" Tests covering the modules commands
"""

import nf_core.modules

import mock
import os
import shutil
import tempfile
import unittest


class TestModules(unittest.TestCase):
    """Class for modules tests"""

    def setUp(self):
        """ Create a new PipelineSchema and Launch objects """
        # Set up the schema
        root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.template_dir = os.path.join(root_repo_dir, "nf_core", "pipeline-template", "{{cookiecutter.name_noslash}}")
        self.pipeline_dir = os.path.join(tempfile.mkdtemp(), "mypipeline")
        shutil.copytree(self.template_dir, self.pipeline_dir)
        self.mods = nf_core.modules.PipelineModules()
        self.mods.pipeline_dir = self.pipeline_dir

    def test_modulesrepo_class(self):
        """ Initialise a modules repo object """
        modrepo = nf_core.modules.ModulesRepo()
        assert modrepo.name == "nf-core/modules"
        assert modrepo.branch == "master"

    def test_modules_list(self):
        """ Test listing available modules """
        self.mods.pipeline_dir = None
        listed_mods = self.mods.list_modules()
        assert "fastqc" in listed_mods

    def test_modules_install_nopipeline(self):
        """ Test installing a module - no pipeline given """
        self.mods.pipeline_dir = None
        assert self.mods.install("foo") is False

    def test_modules_install_emptypipeline(self):
        """ Test installing a module - empty dir given """
        self.mods.pipeline_dir = tempfile.mkdtemp()
        assert self.mods.install("foo") is False

    def test_modules_install_nomodule(self):
        """ Test installing a module - unrecognised module given """
        assert self.mods.install("foo") is False

    def test_modules_install_fastqc(self):
        """ Test installing a module - FastQC """
        assert self.mods.install("fastqc") is not False
        module_path = os.path.join(self.mods.pipeline_dir, "modules", "nf-core", "software", "fastqc")
        assert os.path.exists(module_path)

    def test_modules_install_fastqc_twice(self):
        """ Test installing a module - FastQC already there """
        self.mods.install("fastqc")
        assert self.mods.install("fastqc") is False

    def test_modules_remove_fastqc(self):
        """ Test removing FastQC module after installing it"""
        self.mods.install("fastqc")
        module_path = os.path.join(self.mods.pipeline_dir, "modules", "nf-core", "software", "fastqc")
        assert self.mods.remove("fastqc")
        assert os.path.exists(module_path) is False

    def test_modules_remove_fastqc_uninstalled(self):
        """ Test removing FastQC module without installing it """
        assert self.mods.remove("fastqc") is False
