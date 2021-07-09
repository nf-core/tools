#!/usr/bin/env python
"""
The ModuleCreate class handles generating of module templates
"""

from __future__ import print_function
from packaging.version import parse as parse_version

import glob
import jinja2
import json
import logging
import nf_core
import os
import questionary
import re
import rich
import subprocess
import yaml

import nf_core.utils

log = logging.getLogger(__name__)


class ModuleCreate(object):
    def __init__(
        self, directory=".", tool="", author=None, process_label=None, has_meta=None, force=False, conda_name=None
    ):
        self.directory = directory
        self.tool = tool
        self.author = author
        self.process_label = process_label
        self.has_meta = has_meta
        self.force_overwrite = force
        self.subtool = None
        self.tool_conda_name = conda_name
        self.tool_licence = None
        self.repo_type = None
        self.tool_licence = ""
        self.tool_description = ""
        self.tool_doc_url = ""
        self.tool_dev_url = ""
        self.bioconda = None
        self.singularity_container = None
        self.docker_container = None
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

        modules/modules/tool/subtool/
            * main.nf
            * meta.yml
            * functions.nf
        modules/tests/modules/tool/subtool/
            * main.nf
            * test.yml
        tests/config/pytest_modules.yml

        The function will attempt to automatically find a Bioconda package called <tool>
        and matching Docker / Singularity images from BioContainers.
        """

        # Check whether the given directory is a nf-core pipeline or a clone of nf-core/modules
        try:
            self.repo_type = self.get_repo_type(self.directory)
        except LookupError as e:
            raise UserWarning(e)

        log.info(
            "[yellow]Press enter to use default values [cyan bold](shown in brackets)[/] [yellow]or type your own responses. "
            "ctrl+click [link=https://youtu.be/dQw4w9WgXcQ]underlined text[/link] to open links."
        )

        # Collect module info via prompt if empty or invalid
        if self.tool is None:
            self.tool = ""
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
            self.tool_name = f"{self.tool}/{self.subtool}"
            self.tool_dir = os.path.join(self.tool, self.subtool)

        self.tool_name_underscore = self.tool_name.replace("/", "_")

        # Check existance of directories early for fast-fail
        self.file_paths = self.get_module_dirs()

        # Try to find a bioconda package for 'tool'
        while True:
            try:
                if self.tool_conda_name:
                    anaconda_response = nf_core.utils.anaconda_package(self.tool_conda_name, ["bioconda"])
                else:
                    anaconda_response = nf_core.utils.anaconda_package(self.tool, ["bioconda"])
                version = anaconda_response.get("latest_version")
                if not version:
                    version = str(max([parse_version(v) for v in anaconda_response["versions"]]))
                self.tool_licence = nf_core.utils.parse_anaconda_licence(anaconda_response, version)
                self.tool_description = anaconda_response.get("summary", "")
                self.tool_doc_url = anaconda_response.get("doc_url", "")
                self.tool_dev_url = anaconda_response.get("dev_url", "")
                if self.tool_conda_name:
                    self.bioconda = "bioconda::" + self.tool_conda_name + "=" + version
                else:
                    self.bioconda = "bioconda::" + self.tool + "=" + version
                log.info(f"Using Bioconda package: '{self.bioconda}'")
                break
            except (ValueError, LookupError) as e:
                log.warning(f"Could not find Conda dependency using the Anaconda API: '{self.tool}'")
                if rich.prompt.Confirm.ask(f"[violet]Do you want to enter a different Bioconda package name?"):
                    self.tool_conda_name = rich.prompt.Prompt.ask("[violet]Name of Bioconda package").strip()
                    continue
                else:
                    log.warning(
                        f"{e}\nBuilding module without tool software and meta, you will need to enter this information manually."
                    )
                    break

        # Try to get the container tag (only if bioconda package was found)
        if self.bioconda:
            try:
                if self.tool_conda_name:
                    self.docker_container, self.singularity_container = nf_core.utils.get_biocontainer_tag(
                        self.tool_conda_name, version
                    )
                else:
                    self.docker_container, self.singularity_container = nf_core.utils.get_biocontainer_tag(
                        self.tool, version
                    )
                log.info(f"Using Docker container: '{self.docker_container}'")
                log.info(f"Using Singularity container: '{self.singularity_container}'")
            except (ValueError, LookupError) as e:
                log.info(f"Could not find a Docker/Singularity container ({e})")

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
                log.warning("Does not look like a valid GitHub username (must start with an '@')!")
            self.author = rich.prompt.Prompt.ask(
                "[violet]GitHub Username:[/]{}".format(" (@author)" if author_default is None else ""),
                default=author_default,
            )

        process_label_defaults = ["process_low", "process_medium", "process_high", "process_long"]
        if self.process_label is None:
            log.info(
                "Provide an appropriate resource label for the process, taken from the "
                "[link=https://github.com/nf-core/tools/blob/master/nf_core/pipeline-template/conf/base.config#L29]nf-core pipeline template[/link].\n"
                "For example: {}".format(", ".join(process_label_defaults))
            )
        while self.process_label is None:
            self.process_label = questionary.autocomplete(
                "Process resource label:",
                choices=process_label_defaults,
                style=nf_core.utils.nfcore_question_style,
                default="process_low",
            ).ask()

        if self.has_meta is None:
            log.info(
                "Where applicable all sample-specific information e.g. 'id', 'single_end', 'read_group' "
                "MUST be provided as an input via a Groovy Map called 'meta'. "
                "This information may [italic]not[/] be required in some instances, for example "
                "[link=https://github.com/nf-core/modules/blob/master/modules/bwa/index/main.nf]indexing reference genome files[/link]."
            )
        while self.has_meta is None:
            self.has_meta = rich.prompt.Confirm.ask(
                "[violet]Will the module require a meta map of sample information? (yes/no)", default=True
            )

        # Create module template with cokiecutter
        self.render_template()

        if self.repo_type == "modules":
            # Add entry to pytest_modules.yml
            try:
                with open(os.path.join(self.directory, "tests", "config", "pytest_modules.yml"), "r") as fh:
                    pytest_modules_yml = yaml.safe_load(fh)
                if self.subtool:
                    pytest_modules_yml[self.tool_name] = [
                        f"modules/{self.tool}/{self.subtool}/**",
                        f"tests/modules/{self.tool}/{self.subtool}/**",
                    ]
                else:
                    pytest_modules_yml[self.tool_name] = [
                        f"modules/{self.tool}/**",
                        f"tests/modules/{self.tool}/**",
                    ]
                pytest_modules_yml = dict(sorted(pytest_modules_yml.items()))
                with open(os.path.join(self.directory, "tests", "config", "pytest_modules.yml"), "w") as fh:
                    yaml.dump(pytest_modules_yml, fh, sort_keys=True, Dumper=nf_core.utils.custom_yaml_dumper())
            except FileNotFoundError as e:
                raise UserWarning(f"Could not open 'tests/config/pytest_modules.yml' file!")

        new_files = list(self.file_paths.values())
        if self.repo_type == "modules":
            new_files.append(os.path.join(self.directory, "tests", "config", "pytest_modules.yml"))
        log.info("Created / edited following files:\n  " + "\n  ".join(new_files))

    def render_template(self):
        """
        Create new module files with Jinja2.
        """
        # Run jinja2 for each file in the template folder
        env = jinja2.Environment(loader=jinja2.PackageLoader("nf_core", "module-template"), keep_trailing_newline=True)
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
            template_stat = os.stat(os.path.join(os.path.dirname(nf_core.__file__), "module-template", template_fn))
            os.chmod(dest_fn, template_stat.st_mode)

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
        elif os.path.exists(os.path.join(directory, "modules")):
            return "modules"
        else:
            raise UserWarning(
                f"This directory does not look like a clone of nf-core/modules or an nf-core pipeline: '{directory}'"
                " Please point to a valid directory."
            )

    def get_module_dirs(self):
        """Given a directory and a tool/subtool, set the file paths and check if they already exist

        Returns dict: keys are relative paths to template files, vals are target paths.
        """

        file_paths = {}

        if self.repo_type == "pipeline":
            local_modules_dir = os.path.join(self.directory, "modules", "local")

            # Check whether module file already exists
            module_file = os.path.join(local_modules_dir, f"{self.tool_name}.nf")
            if os.path.exists(module_file) and not self.force_overwrite:
                raise UserWarning(f"Module file exists already: '{module_file}'. Use '--force' to overwrite")

            # If a subtool, check if there is a module called the base tool name already
            if self.subtool and os.path.exists(os.path.join(local_modules_dir, f"{self.tool}.nf")):
                raise UserWarning(f"Module '{self.tool}' exists already, cannot make subtool '{self.tool_name}'")

            # If no subtool, check that there isn't already a tool/subtool
            tool_glob = glob.glob(f"{local_modules_dir}/{self.tool}_*.nf")
            if not self.subtool and tool_glob:
                raise UserWarning(
                    f"Module subtool '{tool_glob[0]}' exists already, cannot make tool '{self.tool_name}'"
                )

            # Set file paths
            file_paths[os.path.join("modules", "main.nf")] = module_file

        if self.repo_type == "modules":
            software_dir = os.path.join(self.directory, "modules", self.tool_dir)
            test_dir = os.path.join(self.directory, "tests", "modules", self.tool_dir)

            # Check if module directories exist already
            if os.path.exists(software_dir) and not self.force_overwrite:
                raise UserWarning(f"Module directory exists: '{software_dir}'. Use '--force' to overwrite")

            if os.path.exists(test_dir) and not self.force_overwrite:
                raise UserWarning(f"Module test directory exists: '{test_dir}'. Use '--force' to overwrite")

            # If a subtool, check if there is a module called the base tool name already
            parent_tool_main_nf = os.path.join(self.directory, "modules", self.tool, "main.nf")
            parent_tool_test_nf = os.path.join(self.directory, "tests", "modules", self.tool, "main.nf")
            if self.subtool and os.path.exists(parent_tool_main_nf):
                raise UserWarning(
                    f"Module '{parent_tool_main_nf}' exists already, cannot make subtool '{self.tool_name}'"
                )
            if self.subtool and os.path.exists(parent_tool_test_nf):
                raise UserWarning(
                    f"Module '{parent_tool_test_nf}' exists already, cannot make subtool '{self.tool_name}'"
                )

            # If no subtool, check that there isn't already a tool/subtool
            tool_glob = glob.glob("{}/*/main.nf".format(os.path.join(self.directory, "modules", self.tool)))
            if not self.subtool and tool_glob:
                raise UserWarning(
                    f"Module subtool '{tool_glob[0]}' exists already, cannot make tool '{self.tool_name}'"
                )

            # Set file paths - can be tool/ or tool/subtool/ so can't do in template directory structure
            file_paths[os.path.join("modules", "functions.nf")] = os.path.join(software_dir, "functions.nf")
            file_paths[os.path.join("modules", "main.nf")] = os.path.join(software_dir, "main.nf")
            file_paths[os.path.join("modules", "meta.yml")] = os.path.join(software_dir, "meta.yml")
            file_paths[os.path.join("tests", "main.nf")] = os.path.join(test_dir, "main.nf")
            file_paths[os.path.join("tests", "test.yml")] = os.path.join(test_dir, "test.yml")

        return file_paths
