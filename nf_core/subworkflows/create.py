"""
The SubworkflowCreate class handles generating of subworkflow templates
"""

from __future__ import print_function

import logging
import os

import yaml

import nf_core
import nf_core.components.components_create
import nf_core.utils
from nf_core.components.components_command import ComponentCommand

log = logging.getLogger(__name__)


class SubworkflowCreate(ComponentCommand):
    def __init__(
        self,
        directory=".",
        subworkflow="",
        author=None,
        force=False,
    ):
        super().__init__("subworkflows", directory)
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

        If <directory> is a clone of nf-core/modules, it creates or modifies the following files:

        subworkflows/nf-core/subworkflow_name/
            * main.nf
            * meta.yml
        tests/subworkflows/nf-core/subworkflow_name/
            * main.nf
            * test.yml
            * nextflow.config
        tests/config/pytest_modules.yml

        """

        # Check whether the given directory is a nf-core pipeline or a clone of nf-core/modules
        log.info(f"Repository type: [blue]{self.repo_type}")
        if self.directory != ".":
            log.info(f"Base directory: '{self.directory}'")

        log.info(
            "[yellow]Press enter to use default values [cyan bold](shown in brackets)[/] [yellow]or type your own responses. "
            "ctrl+click [link=https://youtu.be/dQw4w9WgXcQ]underlined text[/link] to open links."
        )

        # Collect module info via prompt if empty or invalid
        self.subworkflow = nf_core.components.components_create.collect_name_prompt(
            self.subworkflow, self.component_type
        )

        # Determine the tool name
        self.subworkflow_name = self.subworkflow
        self.subworkflow_dir = self.subworkflow

        # Check existence of directories early for fast-fail
        self.file_paths = nf_core.components.components_create.get_component_dirs(
            self.component_type,
            self.repo_type,
            self.directory,
            self.org,
            self.subworkflow_name,
            None,
            None,
            self.subworkflow_dir,
            self.force_overwrite,
        )

        # Prompt for GitHub username
        nf_core.components.components_create.get_username(self.author)

        # Create subworkflow template with jinja2
        nf_core.components.components_create.render_template(self.component_type, vars(self), self.file_paths)

        if self.repo_type == "modules":
            # Add entry to pytest_modules.yml
            try:
                with open(os.path.join(self.directory, "tests", "config", "pytest_modules.yml"), "r") as fh:
                    pytest_modules_yml = yaml.safe_load(fh)
                    pytest_modules_yml["subworkflows/" + self.subworkflow] = [
                        f"subworkflows/{self.org}/{self.subworkflow}/**",
                        f"tests/subworkflows/{self.org}/{self.subworkflow}/**",
                    ]
                pytest_modules_yml = dict(sorted(pytest_modules_yml.items()))
                with open(os.path.join(self.directory, "tests", "config", "pytest_modules.yml"), "w") as fh:
                    yaml.dump(pytest_modules_yml, fh, sort_keys=True, Dumper=nf_core.utils.custom_yaml_dumper())
            except FileNotFoundError:
                raise UserWarning("Could not open 'tests/config/pytest_modules.yml' file!")

        new_files = list(self.file_paths.values())
        if self.repo_type == "modules":
            new_files.append(os.path.join(self.directory, "tests", "config", "pytest_modules.yml"))
        log.info("Created / edited following files:\n  " + "\n  ".join(new_files))
