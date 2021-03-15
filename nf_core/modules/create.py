#!/usr/bin/env python
"""
The ModuleCreate class handles generating of module templates
"""

from __future__ import print_function
from packaging.version import parse as parse_version

import cookiecutter.exceptions
import cookiecutter.main
import json
import logging
import nf_core
import os
import re
import rich
import shutil
import subprocess
import tempfile
import yaml

import nf_core.utils

log = logging.getLogger(__name__)


class ModuleCreate(object):
    def __init__(self, directory=".", tool="", author=None, process_label=None, has_meta=None, force=False):
        self.directory = directory
        self.tool = tool
        self.author = author
        self.process_label = process_label
        self.has_meta = has_meta
        self.force_overwrite = force

        self.subtool = None
        self.tool_licence = None
        self.repo_type = None
        self.bioconda = None
        self.container_tag = None
        self.file_paths = {}

    def create(self):
        """
        Create a new DSL2 module from the nf-core template.

        Tool should be named just <tool> or <tool/subtool>
        e.g fastqc or samtools/sort, respectively.

        If <directory> is a pipeline, this function creates a file called:
        '<directory>/modules/local/tool.nf' 
        OR 
        '<directory>/modules/local/tool_subtool.nf'
        
        If <directory> is a clone of nf-core/modules, it creates or modifies the following files:

        modules/software/tool/subtool/
            * main.nf
            * meta.yml
            * functions.nf
        modules/tests/software/tool/subtool/
            * main.nf
            * test.yml
        tests/config/pytest_software.yml

        The function will attempt to automatically find a Bioconda package called <tool>
        and matching Docker / Singularity images from BioContainers.
        """

        # Check whether the given directory is a nf-core pipeline or a clone of nf-core/modules
        self.repo_type = self.get_repo_type(self.directory)

        log.info(
            "[yellow]Press enter to use default values [cyan bold](shown in brackets) [yellow]or type your own responses"
        )

        # Collect module info via prompt if empty or invalid
        while self.tool == "" or re.search(r"[^a-z\d/]", self.tool) or self.tool.count("/") > 0:

            # Check + auto-fix for invalid chacters
            if re.search(r"[^a-z\d/]", self.tool):
                log.warning("Tool/subtool name must be lower-case letters only, with no punctuation")
                tool_clean = re.sub(r"[^a-z\d/]", "", self.tool.lower())
                if rich.prompt.Confirm.ask(f"[violet]Change '{self.tool}' to '{tool_clean}'?"):
                    self.tool = tool_clean
                else:
                    self.tool = ""

            # Split into tool and subtool
            if self.tool.count("/") > 1:
                log.warning("Tool/subtool can have maximum one '/' character")
                self.tool = ""
            elif self.tool.count("/") == 1:
                self.tool, self.subtool = self.tool.split("/")
            else:
                self.subtool = None  # Reset edge case: entered '/subtool' as name and gone round loop again

            # Prompt for new entry if we reset
            if self.tool == "":
                self.tool = rich.prompt.Prompt.ask("[violet]Name of tool/subtool").strip()

        # Determine the tool name
        self.tool_name = self.tool
        self.tool_dir = self.tool
        if self.subtool:
            self.tool_name = f"{self.tool}_{self.subtool}"
            self.tool_dir = os.path.join(self.tool, self.subtool)

        # Check existance of directories early for fast-fail
        self.file_paths = self.get_module_dirs()

        # Prompt for GitHub username
        # Try to guess the current user if `gh` is installed
        author_default = None
        try:
            with open(os.devnull, "w") as devnull:
                gh_auth_user = json.loads(subprocess.check_output(["gh", "api", "/user"], stderr=devnull))
            author_default = "@{}".format(gh_auth_user["login"])
        except Exception as e:
            log.debug(f"Could not find GitHub username using 'gh' cli command: [red]{e}")

        # Regex to valid GitHub username: https://github.com/shinnn/github-username-regex
        github_username_regex = re.compile(r"^@[a-zA-Z\d](?:[a-zA-Z\d]|-(?=[a-zA-Z\d])){0,38}$")
        while self.author is None or not github_username_regex.match(self.author):
            if self.author is not None and not github_username_regex.match(self.author):
                log.warning("Does not look like a value GitHub username!")
            self.author = rich.prompt.Prompt.ask(
                "[violet]GitHub Username:[/]{}".format(" (@author)" if author_default is None else ""),
                default=author_default,
            )

        if self.process_label is None:
            log.info(
                "Provide an appropriate resource label for the process, taken from the "
                "[link=https://github.com/nf-core/tools/blob/master/nf_core/pipeline-template/%7B%7Bcookiecutter.name_noslash%7D%7D/conf/base.config#L29]nf-core pipeline template[/link].\n"
                "For example: 'process_low', 'process_medium', 'process_high', 'process_long'"
            )
        while self.process_label is None:
            self.process_label = rich.prompt.Prompt.ask("[violet]Process label:", default="process_low")

        if self.has_meta is None:
            log.info(
                "Where applicable all sample-specific information e.g. 'id', 'single_end', 'read_group' "
                "MUST be provided as an input via a Groovy Map called 'meta'. "
                "This information may [italic]not[/] be required in some instances, for example "
                "[link=https://github.com/nf-core/modules/blob/master/software/bwa/index/main.nf]indexing reference genome files[/link]."
            )
        while self.has_meta is None:
            self.has_meta = rich.prompt.Confirm.ask(
                "[violet]Will the module require a meta map of sample information? (yes/no)", default=True
            )

        # Try to find a bioconda package for 'tool'
        try:
            anaconda_response = nf_core.utils.anaconda_package(self.tool, ["bioconda"])
            version = anaconda_response.get("latest_version")
            if not version:
                version = str(max([parse_version(v) for v in anaconda_response["versions"]]))
            self.tool_licence = nf_core.utils.parse_anaconda_licence(anaconda_response, version)
            self.tool_description = anaconda_response.get("summary", "")
            self.tool_doc_url = anaconda_response.get("doc_url", "")
            self.tool_dev_url = anaconda_response.get("dev_url", "")
            self.bioconda = "bioconda::" + self.tool + "=" + version
            log.info(f"Using Bioconda package: '{self.bioconda}'")
        except (ValueError, LookupError) as e:
            log.warning(e)

        # Try to get the container tag (only if bioconda package was found)
        if self.bioconda:
            try:
                self.container_tag = nf_core.utils.get_biocontainer_tag(self.tool, version)
                log.info(f"Using Docker / Singularity container with tag: '{self.container_tag}'")
            except (ValueError, LookupError) as e:
                log.info(f"Could not find a container tag ({e})")

        # Create module template with cokiecutter
        cookiecutter_output = self.run_cookiecutter()

        # Move cookiecutter output files
        for source_fn_base, target_fn in self.file_paths.items():
            source_fn = os.path.join(cookiecutter_output, source_fn_base)
            log.debug(f"Transferring new module file from '{source_fn}' to '{target_fn}'")
            try:
                os.makedirs(os.path.dirname(target_fn), exist_ok=True)
                shutil.move(source_fn, target_fn)
            except OSError as e:
                shutil.rmtree(cookiecutter_output)
                raise UserWarning(f"Could not create module files: {e}")
        shutil.rmtree(cookiecutter_output)

        if self.repo_type == "modules":
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

                with open(os.path.join(self.directory, ".github", "filters.yml"), "w") as fh:
                    yaml.dump(filters_yml, fh, sort_keys=True, Dumper=nf_core.utils.custom_yaml_dumper())
            except FileNotFoundError as e:
                raise UserWarning(f"Could not open filters.yml file!")

        log.info("Created module files:\n  " + "\n  ".join(self.file_paths.values()))

    def run_cookiecutter(self):
        """
        Create new module files with cookiecutter in a temporyary directory.

        Returns: Path to generated files.
        """
        # Build the template in a temporary directory
        tmpdir = tempfile.mkdtemp()
        template = os.path.join(os.path.dirname(os.path.realpath(nf_core.__file__)), "module-template/")
        cookiecutter.main.cookiecutter(
            template,
            extra_context={
                "tool": self.tool,
                "subtool": self.subtool if self.subtool else "",
                "tool_name": self.tool_name,
                "tool_dir": self.tool_dir,
                "author": self.author,
                "bioconda": self.bioconda,
                "container_tag": self.container_tag,
                "label": self.process_label,
                "has_meta": self.has_meta,
                "tool_licence": self.tool_licence,
                "tool_description": self.tool_description,
                "tool_doc_url": self.tool_doc_url,
                "tool_dev_url": self.tool_dev_url,
                "nf_core_version": nf_core.__version__,
            },
            no_input=True,
            overwrite_if_exists=self.force_overwrite,
            output_dir=tmpdir,
        )
        return os.path.join(tmpdir, self.tool_name)

    def get_repo_type(self, directory):
        """
        Determine whether this is a pipeline repository or a clone of
        nf-core/modules
        """
        # Verify that the pipeline dir exists
        if dir is None or not os.path.exists(directory):
            raise UserWarning(f"Could not find directory: {directory}")

        # Determine repository type
        if os.path.exists(os.path.join(directory, "main.nf")):
            return "pipeline"
        elif os.path.exists(os.path.join(directory, "software")):
            return "modules"
        else:
            raise UserWarning(f"Could not determine repository type: '{directory}'")

    def get_module_dirs(self):
        """Given a directory and a tool/subtool, set the file paths and check if they already exist

        Returns dict: keys are file paths in cookiecutter output, vals are target paths.
        """

        file_paths = {}

        if self.repo_type == "pipeline":
            # Check whether module file already exists
            module_file = os.path.join(self.directory, "modules", "local", "process", f"{self.tool_name}.nf")
            if os.path.exists(module_file) and not self.force_overwrite:
                raise UserWarning(f"Module file exists already: '{module_file}'. Use '--force' to overwrite")

            # Set file paths
            file_paths[os.path.join("software", "main.nf")] = module_file

        if self.repo_type == "modules":
            software_dir = os.path.join(self.directory, "software", self.tool_dir)
            test_dir = os.path.join(self.directory, "tests", "software", self.tool_dir)

            # Check if module directories exist already
            if os.path.exists(software_dir) and not self.force_overwrite:
                raise UserWarning(f"Module directory exists: '{software_dir}'. Use '--force' to overwrite")

            if os.path.exists(test_dir) and not self.force_overwrite:
                raise UserWarning(f"Module test directory exists: '{test_dir}'. Use '--force' to overwrite")

            # Set file paths - can be tool/ or tool/subtool/ so can't do in cookiecutter template
            file_paths[os.path.join("software", "functions.nf")] = os.path.join(software_dir, "functions.nf")
            file_paths[os.path.join("software", "main.nf")] = os.path.join(software_dir, "main.nf")
            file_paths[os.path.join("software", "meta.yml")] = os.path.join(software_dir, "meta.yml")
            file_paths[os.path.join("tests", "main.nf")] = os.path.join(test_dir, "main.nf")
            file_paths[os.path.join("tests", "test.yml")] = os.path.join(test_dir, "test.yml")

        return file_paths
