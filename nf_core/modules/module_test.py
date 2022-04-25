#!/usr/bin/env python
"""
The ModulesTest class runs the tests locally
"""

import logging
import questionary
import os

"""from __future__ import print_function
from rich.syntax import Syntax

import errno
import gzip
import hashlib
import operator


import re
import rich
import shlex
import subprocess
import tempfile
import yaml

"""
import nf_core.utils
from .modules_repo import ModulesRepo
from .test_yml_builder import ModulesTestYmlBuilder

log = logging.getLogger(__name__)


class ModulesTest(ModulesTestYmlBuilder):
    def __init__(
        self,
        module_name=None,
        no_prompts=False,
    ):
        self.run_tests = True
        self.module_name = module_name
        self.no_prompts = no_prompts
        self.module_dir = None
        self.module_test_main = None
        self.entry_points = []
        self.tests = []
        self.errors = []

    def run(self):
        """Run test steps"""
        if not self.no_prompts:
            log.info(
                "[yellow]Press enter to use default values [cyan bold](shown in brackets) [yellow]or type your own responses"
            )
        self.check_inputs_test()
        self.scrape_workflow_entry_points()
        self.build_all_tests()
        if len(self.errors) > 0:
            errors = "\n - ".join(self.errors)
            raise UserWarning(f"Ran, but found errors:\n - {errors}")

    def check_inputs_test(self):
        """Do more complex checks about supplied flags."""

        # Get the tool name if not specified
        if self.module_name is None:
            modules_repo = ModulesRepo()
            modules_repo.get_modules_file_tree()
            self.module_name = questionary.autocomplete(
                "Tool name:",
                choices=modules_repo.modules_avail_module_names,
                style=nf_core.utils.nfcore_question_style,
            ).ask()
        self.module_dir = os.path.join("modules", *self.module_name.split("/"))
        self.module_test_main = os.path.join("tests", "modules", *self.module_name.split("/"), "main.nf")

        # First, sanity check that the module directory exists
        if not os.path.isdir(self.module_dir):
            raise UserWarning(f"Cannot find directory '{self.module_dir}'. Should be TOOL/SUBTOOL or TOOL")
        if not os.path.exists(self.module_test_main):
            raise UserWarning(f"Cannot find module test workflow '{self.module_test_main}'")
