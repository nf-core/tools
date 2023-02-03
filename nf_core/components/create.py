"""
The ComponentCreate class handles generating of module and subworkflow templates
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
import nf_core.utils
from nf_core.components.components_command import ComponentCommand

log = logging.getLogger(__name__)


class ComponentCreate(ComponentCommand):
    def __init__(
        self,
        component_type,
        directory=".",
        component="",
        author=None,
        process_label=None,
        has_meta=None,
        force=False,
        conda_name=None,
        conda_version=None,
        empty_template=False,
    ):
        super().__init__(component_type, directory)
        self.directory = directory
        self.component = component
        self.author = author
        self.process_label = process_label
        self.has_meta = has_meta
        self.force_overwrite = force
        self.subtool = None
        self.tool_conda_name = conda_name
        self.tool_conda_version = conda_version
        self.tool_licence = None
        self.tool_licence = ""
        self.tool_description = ""
        self.tool_doc_url = ""
        self.tool_dev_url = ""
        self.bioconda = None
        self.singularity_container = None
        self.docker_container = None
        self.file_paths = {}
        self.not_empty_template = not empty_template

    def create(self):
        """
        Create a new DSL2 module or subworkflow from the nf-core template.

        A module should be named just <tool> or <tool/subtool>
        e.g fastqc or samtools/sort, respectively.

        The subworkflow should be named as the main file type it operates on and a short description of the task performed
        e.g bam_sort or bam_sort_samtools, respectively.

        If <directory> is a pipeline, this function creates a file called:
        '<directory>/modules/local/tool.nf'
          OR
        '<directory>/modules/local/tool_subtool.nf'
          OR for subworkflows
        '<directory>/subworkflows/local/subworkflow_name.nf'

        If <directory> is a clone of nf-core/modules, it creates or modifies the following files:

        For modules:

        modules/modules/nf-core/tool/subtool/
            * main.nf
            * meta.yml
        modules/tests/modules/nf-core/tool/subtool/
            * main.nf
            * test.yml
            * nextflow.config
        tests/config/pytest_modules.yml

        The function will attempt to automatically find a Bioconda package called <component>
        and matching Docker / Singularity images from BioContainers.

        For subworkflows:
        subworkflows/nf-core/subworkflow_name/
            * main.nf
            * meta.yml
        tests/subworkflows/nf-core/subworkflow_name/
            * main.nf
            * test.yml
            * nextflow.config
        tests/config/pytest_modules.yml

        """

        if self.component_type == "modules":
            # Check modules directory structure
            self.check_modules_structure()

        # Check whether the given directory is a nf-core pipeline or a clone of nf-core/modules
        log.info(f"Repository type: [blue]{self.repo_type}")
        if self.directory != ".":
            log.info(f"Base directory: '{self.directory}'")

        log.info(
            "[yellow]Press enter to use default values [cyan bold](shown in brackets)[/] [yellow]or type your own responses. "
            "ctrl+click [link=https://youtu.be/dQw4w9WgXcQ]underlined text[/link] to open links."
        )

        # Collect component info via prompt if empty or invalid
        self._collect_name_prompt()

        # Determine the component name
        self.component_name = self.component
        self.component_dir = self.component

        if self.subtool:
            self.component_name = f"{self.component}/{self.subtool}"
            self.component_dir = os.path.join(self.component, self.subtool)

        self.component_name_underscore = self.component_name.replace("/", "_")

        # Check existence of directories early for fast-fail
        self.file_paths = self._get_component_dirs()

        if self.component_type == "modules":
            # Try to find a bioconda package for 'component'
            self._get_bioconda_tool()

        # Prompt for GitHub username
        self._get_username()

        if self.component_type == "modules":
            self._get_module_structure_components()

        # Create component template with jinja2
        self._render_template()

        if self.repo_type == "modules":
            # Add entry to pytest_modules.yml
            try:
                with open(os.path.join(self.directory, "tests", "config", "pytest_modules.yml"), "r") as fh:
                    pytest_modules_yml = yaml.safe_load(fh)
                if self.subtool:
                    pytest_modules_yml[self.component_name] = [
                        f"modules/{self.org}/{self.component}/{self.subtool}/**",
                        f"tests/modules/{self.org}/{self.component}/{self.subtool}/**",
                    ]
                else:
                    pytest_modules_yml[
                        ("" if self.component_type == "modules" else self.component_type + "/") + self.component_name
                    ] = [
                        f"{self.component_type}/{self.org}/{self.component}/**",
                        f"tests/{self.component_type}/{self.org}/{self.component}/**",
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

    def _get_bioconda_tool(self):
        """
        Try to find a bioconda package for 'tool'
        """
        while True:
            try:
                if self.tool_conda_name:
                    anaconda_response = nf_core.utils.anaconda_package(self.tool_conda_name, ["bioconda"])
                else:
                    anaconda_response = nf_core.utils.anaconda_package(self.component, ["bioconda"])

                if not self.tool_conda_version:
                    version = anaconda_response.get("latest_version")
                    if not version:
                        version = str(max([parse_version(v) for v in anaconda_response["versions"]]))
                else:
                    version = self.tool_conda_version

                self.tool_licence = nf_core.utils.parse_anaconda_licence(anaconda_response, version)
                self.tool_description = anaconda_response.get("summary", "")
                self.tool_doc_url = anaconda_response.get("doc_url", "")
                self.tool_dev_url = anaconda_response.get("dev_url", "")
                if self.tool_conda_name:
                    self.bioconda = "bioconda::" + self.tool_conda_name + "=" + version
                else:
                    self.bioconda = "bioconda::" + self.component + "=" + version
                log.info(f"Using Bioconda package: '{self.bioconda}'")
                break
            except (ValueError, LookupError) as e:
                log.warning(
                    f"Could not find Conda dependency using the Anaconda API: '{self.tool_conda_name if self.tool_conda_name else self.component}'"
                )
                if rich.prompt.Confirm.ask("[violet]Do you want to enter a different Bioconda package name?"):
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
                        self.component, version
                    )
                log.info(f"Using Docker container: '{self.docker_container}'")
                log.info(f"Using Singularity container: '{self.singularity_container}'")
            except (ValueError, LookupError) as e:
                log.info(f"Could not find a Docker/Singularity container ({e})")

    def _get_module_structure_components(self):
        process_label_defaults = ["process_single", "process_low", "process_medium", "process_high", "process_long"]
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
                default="process_single",
            ).unsafe_ask()

        if self.has_meta is None:
            log.info(
                "Where applicable all sample-specific information e.g. 'id', 'single_end', 'read_group' "
                "MUST be provided as an input via a Groovy Map called 'meta'. "
                "This information may [italic]not[/] be required in some instances, for example "
                "[link=https://github.com/nf-core/modules/blob/master/modules/nf-core/bwa/index/main.nf]indexing reference genome files[/link]."
            )
        while self.has_meta is None:
            self.has_meta = rich.prompt.Confirm.ask(
                "[violet]Will the module require a meta map of sample information?", default=True
            )

    def _render_template(self):
        """
        Create new module/subworkflow files with Jinja2.
        """
        object_attrs = vars(self)
        # Run jinja2 for each file in the template folder
        env = jinja2.Environment(
            loader=jinja2.PackageLoader("nf_core", f"{self.component_type[:-1]}-template"), keep_trailing_newline=True
        )
        for template_fn, dest_fn in self.file_paths.items():
            log.debug(f"Rendering template file: '{template_fn}'")
            j_template = env.get_template(template_fn)
            object_attrs["nf_core_version"] = nf_core.__version__
            rendered_output = j_template.render(object_attrs)

            # Write output to the target file
            os.makedirs(os.path.dirname(dest_fn), exist_ok=True)
            with open(dest_fn, "w") as fh:
                log.debug(f"Writing output to: '{dest_fn}'")
                fh.write(rendered_output)

            # Mirror file permissions
            template_stat = os.stat(
                os.path.join(os.path.dirname(nf_core.__file__), f"{self.component_type[:-1]}-template", template_fn)
            )
            os.chmod(dest_fn, template_stat.st_mode)

    def _collect_name_prompt(self):
        """
        Collect module/subworkflow info via prompt if empty or invalid
        """
        # Collect module info via prompt if empty or invalid
        self.subtool = None
        if self.component_type == "modules":
            pattern = r"[^a-z\d/]"
        elif self.component_type == "subworkflows":
            pattern = r"[^a-z\d_/]"
        if self.component is None:
            self.component = ""
        while self.component == "" or re.search(pattern, self.component) or self.component.count("/") > 0:
            # Check + auto-fix for invalid chacters
            if re.search(pattern, self.component):
                if self.component_type == "modules":
                    log.warning("Tool/subtool name must be lower-case letters only, with no punctuation")
                elif self.component_type == "subworkflows":
                    log.warning("Subworkflow name must be lower-case letters only, with no punctuation")
                name_clean = re.sub(r"[^a-z\d/]", "", self.component.lower())
                if rich.prompt.Confirm.ask(f"[violet]Change '{self.component}' to '{name_clean}'?"):
                    self.component = name_clean
                else:
                    self.component = ""

            if self.component_type == "modules":
                # Split into tool and subtool
                if self.component.count("/") > 1:
                    log.warning("Tool/subtool can have maximum one '/' character")
                    self.component = ""
                elif self.component.count("/") == 1:
                    self.component, self.subtool = self.component.split("/")
                else:
                    self.subtool = None  # Reset edge case: entered '/subtool' as name and gone round loop again

            # Prompt for new entry if we reset
            if self.component == "":
                if self.component_type == "modules":
                    self.component = rich.prompt.Prompt.ask("[violet]Name of tool/subtool").strip()
                elif self.component_type == "subworkflows":
                    self.component = rich.prompt.Prompt.ask("[violet]Name of subworkflow").strip()

    def _get_component_dirs(self):
        """Given a directory and a tool/subtool or subworkflow, set the file paths and check if they already exist

        Returns dict: keys are relative paths to template files, vals are target paths.
        """
        file_paths = {}
        if self.repo_type == "pipeline":
            local_component_dir = os.path.join(self.directory, self.component_type, "local")
            # Check whether component file already exists
            component_file = os.path.join(local_component_dir, f"{self.component_name}.nf")
            if os.path.exists(component_file) and not self.force_overwrite:
                raise UserWarning(
                    f"{self.component_type[:-1].title()} file exists already: '{component_file}'. Use '--force' to overwrite"
                )

            if self.component_type == "modules":
                # If a subtool, check if there is a module called the base tool name already
                if self.subtool and os.path.exists(os.path.join(local_component_dir, f"{self.component}.nf")):
                    raise UserWarning(
                        f"Module '{self.component}' exists already, cannot make subtool '{self.component_name}'"
                    )

                # If no subtool, check that there isn't already a tool/subtool
                tool_glob = glob.glob(f"{local_component_dir}/{self.component}_*.nf")
                if not self.subtool and tool_glob:
                    raise UserWarning(
                        f"Module subtool '{tool_glob[0]}' exists already, cannot make tool '{self.component_name}'"
                    )

            # Set file paths
            file_paths[os.path.join(self.component_type, "main.nf")] = component_file

        if self.repo_type == "modules":
            software_dir = os.path.join(self.directory, self.component_type, self.org, self.component_dir)
            test_dir = os.path.join(self.directory, "tests", self.component_type, self.org, self.component_dir)

            # Check if module/subworkflow directories exist already
            if os.path.exists(software_dir) and not self.force_overwrite:
                raise UserWarning(
                    f"{self.component_type[:-1]} directory exists: '{software_dir}'. Use '--force' to overwrite"
                )
            if os.path.exists(test_dir) and not self.force_overwrite:
                raise UserWarning(
                    f"{self.component_type[:-1]} test directory exists: '{test_dir}'. Use '--force' to overwrite"
                )

            if self.component_type == "modules":
                # If a subtool, check if there is a module called the base tool name already
                parent_tool_main_nf = os.path.join(
                    self.directory, self.component_type, self.org, self.component, "main.nf"
                )
                parent_tool_test_nf = os.path.join(
                    self.directory, self.component_type, self.org, self.component, "main.nf"
                )
                if self.subtool and os.path.exists(parent_tool_main_nf):
                    raise UserWarning(
                        f"Module '{parent_tool_main_nf}' exists already, cannot make subtool '{self.component_name}'"
                    )
                if self.subtool and os.path.exists(parent_tool_test_nf):
                    raise UserWarning(
                        f"Module '{parent_tool_test_nf}' exists already, cannot make subtool '{self.component_name}'"
                    )

                # If no subtool, check that there isn't already a tool/subtool
                tool_glob = glob.glob(
                    f"{os.path.join(self.directory, self.component_type, self.org, self.component)}/*/main.nf"
                )
                if not self.subtool and tool_glob:
                    raise UserWarning(
                        f"Module subtool '{tool_glob[0]}' exists already, cannot make tool '{self.component_name}'"
                    )

            # Set file paths
            # For modules - can be tool/ or tool/subtool/ so can't do in template directory structure
            file_paths[os.path.join(self.component_type, "main.nf")] = os.path.join(software_dir, "main.nf")
            file_paths[os.path.join(self.component_type, "meta.yml")] = os.path.join(software_dir, "meta.yml")
            file_paths[os.path.join("tests", "main.nf")] = os.path.join(test_dir, "main.nf")
            file_paths[os.path.join("tests", "test.yml")] = os.path.join(test_dir, "test.yml")
            file_paths[os.path.join("tests", "nextflow.config")] = os.path.join(test_dir, "nextflow.config")

        return file_paths

    def _get_username(self):
        """
        Prompt for GitHub username
        """
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
