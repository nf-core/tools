#!/usr/bin/env python
"""
The SubworkflowCreate class handles generating of subworkflow templates
"""

from __future__ import print_function

import glob
import json
import logging
import os
import re
import subprocess

import jinja2
import questionary
import rich
import yaml
from packaging.version import parse as parse_version

import nf_core
from nf_core.modules.module_utils import get_repo_type
import nf_core.utils

log = logging.getLogger(__name__)


class SubworkflowCreate(object):
    def __init__(
        self,
        directory=".",
        subworkflow="",
        author=None,
        force=False,
    ):
        self.directory = directory
        self.subworkflow = subworkflow
        self.author = author
        self.force_overwrite = force
        self.file_paths = {}

    def create(self):
        """
        Create a new subworkflow from the nf-core template.

        The subworkflow should be named as the main file type it operates on and a short description of the task performed
        e.g bam_sort or bam_sort_samtools, respectively.

        If <directory> is a pipeline, this function creates a file called:
        '<directory>/subworkflows/local/subworkflow_name.nf'
            OR
        '<directory>/subworkflows/local/subworkflow_name.nf'

        If <directory> is a clone of nf-core/modules, it creates or modifies the following files:

        subworkflows/subworkflow_name/
            * main.nf
            * meta.yml
        tests/subworkflows/subworkflow_name/
            * main.nf
            * test.yml
            * nextflow.config
        tests/config/pytest_subworkflows.yml

        """

        # Check whether the given directory is a nf-core pipeline or a clone of nf-core/modules
        try:
            self.directory, self.repo_type = get_repo_type(self.directory, self.repo_type)
        except LookupError as e:
            raise UserWarning(e)
        log.info(f"Repository type: [blue]{self.repo_type}")
        if self.directory != ".":
            log.info(f"Base directory: '{self.directory}'")

        log.info(
            "[yellow]Press enter to use default values [cyan bold](shown in brackets)[/] [yellow]or type your own responses. "
            "ctrl+click [link=https://youtu.be/dQw4w9WgXcQ]underlined text[/link] to open links."
        )

        # Collect module info via prompt if empty or invalid
        if self.subworkflow is None:
            self.subworkflow = ""
        while self.subworkflow == "" or re.search(r"[^a-z\d/]", self.subworkflow) or self.subworkflow.count("/") > 0:

            # Check + auto-fix for invalid chacters
            if re.search(r"[^a-z\d/]", self.subworkflow):
                log.warning("Subworkflow name must be lower-case letters only, with no punctuation")
                subworkflow_clean = re.sub(r"[^a-z\d/]", "", self.subworkflow.lower())
                if rich.prompt.Confirm.ask(f"[violet]Change '{self.subworkflow}' to '{subworkflow_clean}'?"):
                    self.subworkflow = subworkflow_clean
                else:
                    self.subworkflow = ""

            # Prompt for new entry if we reset
            if self.subworkflow == "":
                self.subworkflow = rich.prompt.Prompt.ask("[violet]Name of subworkflow").strip()

        # Determine the tool name
        self.subworkflow_name = self.subworkflow
        self.subworkflow_dir = self.subworkflow

        # Check existence of directories early for fast-fail
        self.file_paths = self.get_subworkflow_dirs()

        # Prompt for GitHub username
        # Try to guess the current user if `gh` is installed
        author_default = None
        try:
            with open(os.devnull, "w") as devnull:
                gh_auth_user = json.loads(subprocess.check_output(["gh", "api", "/user"], stderr=devnull))
            author_default = f"@{gh_auth_user['login']}"
        except Exception as e:
            log.debug(f"Could not find GitHub username using 'gh' cli command: [red]{e}")

        # Regex to valid GitHub username: https://github.com/shinnn/github-username-regex
        github_username_regex = re.compile(r"^@[a-zA-Z\d](?:[a-zA-Z\d]|-(?=[a-zA-Z\d])){0,38}$")
        while self.author is None or not github_username_regex.match(self.author):
            if self.author is not None and not github_username_regex.match(self.author):
                log.warning("Does not look like a valid GitHub username (must start with an '@')!")
            self.author = rich.prompt.Prompt.ask(
                f"[violet]GitHub Username:[/]{' (@author)' if author_default is None else ''}",
                default=author_default,
            )

        # Create module template with jinja2
        self.render_template()

        if self.repo_type == "modules":
            # Add entry to pytest_subworkflows.yml
            try:
                with open(os.path.join(self.directory, "tests", "config", "pytest_subworkflows.yml"), "r") as fh:
                    pytest_subworkflows_yml = yaml.safe_load(fh)
                    pytest_subworkflows_yml[self.subworkflow_name] = [
                        f"subworkflows/{self.subworkflow}/**",
                        f"tests/subworkflows/{self.subworkflow}/**",
                    ]
                pytest_subworkflows_yml = dict(sorted(pytest_subworkflows_yml.items()))
                with open(os.path.join(self.directory, "tests", "config", "pytest_subworkflows.yml"), "w") as fh:
                    yaml.dump(pytest_subworkflows_yml, fh, sort_keys=True, Dumper=nf_core.utils.custom_yaml_dumper())
            except FileNotFoundError as e:
                raise UserWarning("Could not open 'tests/config/pytest_modules.yml' file!")

        new_files = list(self.file_paths.values())
        if self.repo_type == "modules":
            new_files.append(os.path.join(self.directory, "tests", "config", "pytest_modules.yml"))
        log.info("Created / edited following files:\n  " + "\n  ".join(new_files))

    def render_template(self):
        """
        Create new subworkflow files with Jinja2.
        """
        # Run jinja2 for each file in the template folder
        env = jinja2.Environment(
            loader=jinja2.PackageLoader("nf_core", "subworkflow-template"), keep_trailing_newline=True
        )
        for template_fn, dest_fn in self.file_paths.items():
            log.debug(f"Rendering template file: '{template_fn}'")
            j_template = env.get_template(template_fn)
            object_attrs = vars(self)
            object_attrs["nf_core_version"] = nf_core.__version__
            rendered_output = j_template.render(object_attrs)

            # Write output to the target file
            os.makedirs(os.path.dirname(dest_fn), exist_ok=True)
            with open(dest_fn, "w") as fh:
                log.debug(f"Writing output to: '{dest_fn}'")
                fh.write(rendered_output)

            # Mirror file permissions
            template_stat = os.stat(
                os.path.join(os.path.dirname(nf_core.__file__), "subworkflow-template", template_fn)
            )
            os.chmod(dest_fn, template_stat.st_mode)

    def get_subworkflow_dirs(self):
        """Given a directory and a subworkflow, set the file paths and check if they already exist

        Returns dict: keys are relative paths to template files, vals are target paths.
        """

        file_paths = {}

        if self.repo_type == "pipeline":
            local_subworkflow_dir = os.path.join(self.directory, "subworkflows", "local")

            # Check whether subworkflow file already exists
            subworkflow_file = os.path.join(local_subworkflow_dir, f"{self.subworkflow_name}.nf")
            if os.path.exists(subworkflow_file) and not self.force_overwrite:
                raise UserWarning(f"Subworkflow file exists already: '{subworkflow_file}'. Use '--force' to overwrite")

            # Set file paths
            file_paths[os.path.join("subworkflows", f"{self.subworkflow_name}.nf")] = subworkflow_file

        if self.repo_type == "modules":
            subworkflow_path = os.path.join(self.directory, "subworkflows", self.subworkflow_dir)
            test_dir = os.path.join(self.directory, "tests", "subworkflows", self.subworkflow_dir)

            # Check if module directories exist already
            if os.path.exists(subworkflow_path) and not self.force_overwrite:
                raise UserWarning(f"Subworkflow directory exists: '{subworkflow_path}'. Use '--force' to overwrite")

            if os.path.exists(test_dir) and not self.force_overwrite:
                raise UserWarning(f"Subworkflow test directory exists: '{test_dir}'. Use '--force' to overwrite")

            # Set file paths
            file_paths[os.path.join("subworkflows", "main.nf")] = os.path.join(subworkflow_path, "main.nf")
            file_paths[os.path.join("subworkflows", "meta.yml")] = os.path.join(subworkflow_path, "meta.yml")
            file_paths[os.path.join("tests", "main.nf")] = os.path.join(test_dir, "main.nf")
            file_paths[os.path.join("tests", "test.yml")] = os.path.join(test_dir, "test.yml")
            file_paths[os.path.join("tests", "nextflow.config")] = os.path.join(test_dir, "nextflow.config")

        return file_paths
