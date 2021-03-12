#!/usr/bin/env python
"""
The ModuleCreate class handles generating of module templates
"""

from __future__ import print_function

import cookiecutter.exceptions
import cookiecutter.main
import logging
import nf_core
import os
import re
import rich
import shutil
import sys
import tempfile
import yaml

import nf_core.utils

log = logging.getLogger(__name__)


class ModuleCreate(object):
    def __init__(self, directory=".", tool=None, subtool=None):
        self.directory = directory
        self.tool = tool
        self.subtool = subtool
        self.author = None
        self.label = None
        self.has_meta = None

    def create(self, force=False, no_prompts=False):
        """
        Create a new module from the template

        If <directory> is a ppipeline, this function creates a file in the
        'directory/modules/local/process' dir called <tool_subtool.nf>

        If <directory> is a clone of nf-core/modules, it creates the files and
        corresponding directories:

        modules/software/tool/subtool/
            * main.nf
            * meta.yml
            * functions.nf

        modules/tests/software/tool/subtool/
            * main.nf
            * test.yml

        Additionally the necessary lines to run the tests are appended to
        modules/.github/filters.yml
        The function will also try to look for a bioconda package called 'tool'
        and for a matching container on quay.io

        :param directory:   the target directory to create the module template in
        :param tool:        name of the tool
        :param subtool:     name of the
        """
        self.force = force
        self.no_prompts = no_prompts
        # Check whether the given directory is a nf-core pipeline or a clone
        # of nf-core modules
        self.repo_type = self.get_repo_type(self.directory)

        # Collect module info via prompt if not already given
        if not self.no_prompts or self.tool is None:
            log.info(
                "[yellow]Press enter to use default values [cyan bold](shown in brackets) [yellow]or type your own responses"
            )
        while self.tool is None or self.tool == "" or re.search(r"[^a-z]", self.tool):
            if self.tool is not None and re.search(r"[^a-z]", self.tool):
                log.warning("Tool name must be lower-case letters only, with no punctuation")
                tool_clean = re.sub(r"[^a-z]", "", self.tool.lower())
                if rich.prompt.Confirm.ask(f"[violet]Change '{self.tool}' to '{tool_clean}'?") or self.no_prompts:
                    self.tool = tool_clean
                    continue
            self.tool = rich.prompt.Prompt.ask("[violet]Tool name").strip()

        while self.subtool is None or re.search(r"[^a-z]", self.subtool):
            if self.subtool is not None and re.search(r"[^a-z]", self.subtool):
                log.warning("Subtool name must be lower-case letters only, with no punctuation")
                subtool_clean = re.sub(r"[^a-z]", "", self.subtool.lower())
                if rich.prompt.Confirm.ask(f"[violet]Change '{self.subtool}' to '{subtool_clean}'?") or self.no_prompts:
                    self.subtool = subtool_clean
                    continue
            self.subtool = rich.prompt.Prompt.ask("[violet]Subtool name[/] (leave empty if no subtool)", default=None)
            if self.subtool == "":
                self.subtool = False

        # https://github.com/shinnn/github-username-regex
        github_username_regex = re.compile(r"^@[a-zA-Z\d](?:[a-zA-Z\d]|-(?=[a-zA-Z\d])){0,38}$")
        while self.author is None or not github_username_regex.match(self.author):
            if self.no_prompts:
                self.author = "@nf_core"
            else:
                if self.author is not None and not github_username_regex.match(self.author):
                    log.warning("Does not look like a value GitHub username!")
                self.author = rich.prompt.Prompt.ask("[violet]GitHub Username:[/] (@author)")

        while self.label is None:
            if self.no_prompts:
                self.label = "process_low"
            else:
                self.label = rich.prompt.Prompt.ask("[violet]Process label:", default="process_low")

        while self.has_meta is None:
            if self.no_prompts:
                self.has_meta = True
            else:
                self.has_meta = rich.prompt.Confirm.ask("[violet]Use meta tag? (yes/no)")

        # Determine the tool name
        self.tool_name = self.tool
        self.tool_dir = self.tool
        if self.subtool:
            self.tool_name += "_" + self.subtool
            self.tool_dir += "/" + self.subtool

        # Try to find a bioconda package for 'tool'
        self.bioconda = None
        try:
            response = nf_core.utils.anaconda_package(self.tool, has_version=False)
            version = max(response["versions"])
            self.bioconda = "bioconda::" + self.tool + "=" + version
            log.info(f"Using bioconda package: {self.bioconda}")
        except (ValueError, LookupError) as e:
            log.warning(e)

        # Try to get the container tag (only if bioconda package was found)
        self.container_tag = None
        if self.bioconda:
            try:
                self.container_tag = nf_core.utils.get_biocontainer_tag(self.tool, version)
                log.info(f"Using docker/singularity container with tag: {self.container_tag}")
            except (ValueError, LookupError) as e:
                log.info(f"Could not find a container tag ({e})")

        # Create module template with cokiecutter
        self.run_cookiecutter()

        # Create template for new module in nf-core pipeline
        if self.repo_type == "pipeline":
            # Check whether module file already exists
            module_file = os.path.join(self.directory, "modules", "local", "process", self.tool_name + ".nf")
            if os.path.exists(module_file) and not self.force:
                if rich.prompt.Confirm.ask(f"[red]File exists! [green]'{module_file}' [violet]Overwrite?"):
                    self.force = True
                if not self.force:
                    raise UserWarning(f"Module file exists already: '{module_file}'. Use '--force' to overwrite")

            # Create directory and add the module template file
            outdir = os.path.join(os.getcwd(), self.directory, "modules", "local", "process")
            try:
                os.makedirs(outdir, exist_ok=True)
                shutil.move(
                    os.path.join(self.tmpdir, self.tool_name, self.tool_name + ".nf"),
                    os.path.join(outdir, self.tool_name + ".nf"),
                )

            except OSError as e:
                shutil.rmtree(self.tmpdir)
                raise UserWarning(f"Could not create module file {module_file}: {e}")
            shutil.rmtree(self.tmpdir)

        # Create template for new module in nf-core/modules repository clone
        if self.repo_type == "modules":
            self.software_dir = os.path.join(self.directory, "software", self.tool_dir)
            self.test_dir = os.path.join(self.directory, "tests", "software", self.tool_dir)

            # Check if module directories exist already
            # If yes (and --force not specified) ask whether we should overwrite them
            if os.path.exists(self.software_dir) and not self.force:
                if rich.prompt.Confirm.ask(
                    f"[red]Module directory exists already! [green]'{self.software_dir}' [violet]Overwrite?"
                ):
                    self.force = True
                if not self.force:
                    raise UserWarning(
                        f"Module directory exists already: '{self.software_dir}'. Use '--force' to overwrite"
                    )

            if os.path.exists(self.test_dir) and not self.force:
                if rich.prompt.Confirm.ask(
                    f"[red]Module test directory exists already! [green]'{self.test_dir}' [violet]Overwrite?"
                ):
                    self.force = True
                if not self.force:
                    raise UserWarning(
                        f"Module test directory exists already: '{self.test_dir}'. Use '--force' to overwrite"
                    )

            # Create directories and populate with template module files
            try:
                # software dir (software/tool/subtool)
                os.makedirs(self.software_dir, exist_ok=True)
                shutil.move(
                    os.path.join(self.tmpdir, self.tool_name, "software", "main.nf"),
                    os.path.join(os.getcwd(), self.software_dir, "main.nf"),
                )
                shutil.move(
                    os.path.join(self.tmpdir, self.tool_name, "software", "functions.nf"),
                    os.path.join(os.getcwd(), self.software_dir, "functions.nf"),
                )
                shutil.move(
                    os.path.join(self.tmpdir, self.tool_name, "software", "meta.yml"),
                    os.path.join(os.getcwd(), self.software_dir, "meta.yml"),
                )

                # testdir (tests/software/tool/subtool)
                os.makedirs(self.test_dir, exist_ok=True)
                shutil.move(
                    os.path.join(self.tmpdir, self.tool_name, "tests", "main.nf"),
                    os.path.join(os.getcwd(), self.test_dir, "main.nf"),
                )
                shutil.move(
                    os.path.join(self.tmpdir, self.tool_name, "tests", "test.yml"),
                    os.path.join(os.getcwd(), self.test_dir, "test.yml"),
                )

            except OSError as e:
                shutil.rmtree(self.tmpdir)
                raise UserWarning(f"Could not create module files: {e}")
            shutil.rmtree(self.tmpdir)

            # Add entry to filters.yml
            try:
                with open(os.path.join(self.directory, ".github", "filters.yml"), "r") as fh:
                    filters_yml = yaml.safe_load(fh)
                if self.subtool:
                    filters_yml[self.tool_name] = [
                        f"software/{self.tool}/{self.subtool}/**",
                        f"tests/software/{self.tool}/{self.subtool}/**",
                    ]
                else:
                    filters_yml[self.tool_name] = [
                        f"software/{self.tool}/**",
                        f"tests/software/{self.tool}/**",
                    ]

                CustomDumper = nf_core.utils.custom_yaml_dumper()
                with open(os.path.join(self.directory, ".github", "filters.yml"), "w") as fh:
                    yaml.dump(filters_yml, fh, sort_keys=True, Dumper=CustomDumper)
            except FileNotFoundError as e:
                raise UserWarning(f"Could not open filters.yml file!")

            log.info(f"Created module files: '{self.software_dir}'")
            log.info(f"Created test files: '{self.test_dir}'")

    def run_cookiecutter(self):
        """ Create new module templates with cookiecutter """
        # Build the template in a temporary directory
        self.tmpdir = tempfile.mkdtemp()
        template = os.path.join(os.path.dirname(os.path.realpath(nf_core.__file__)), "module-template/")
        subtool = ""
        if self.subtool:
            subtool = self.subtool
        cookiecutter.main.cookiecutter(
            template,
            extra_context={
                "tool": self.tool,
                "subtool": subtool,
                "tool_name": self.tool_name,
                "tool_dir": self.tool_dir,
                "author": self.author,
                "bioconda": self.bioconda,
                "container_tag": self.container_tag,
                "label": self.label,
                "has_meta": self.has_meta,
                "nf_core_version": nf_core.__version__,
            },
            no_input=True,
            overwrite_if_exists=self.force,
            output_dir=self.tmpdir,
        )

    def get_repo_type(self, directory):
        """
        Determine whether this is a pipeline repository or a clone of
        nf-core/modules
        """
        # Verify that the pipeline dir exists
        if dir is None or not os.path.exists(directory):
            log.error("Could not find directory: {}".format(directory))
            sys.exit(1)

        # Determine repository type
        if os.path.exists(os.path.join(directory, "main.nf")):
            return "pipeline"
        elif os.path.exists(os.path.join(directory, "software")):
            return "modules"
        else:
            log.error("Could not determine repository type of {}".format(directory))
            sys.exit(1)
