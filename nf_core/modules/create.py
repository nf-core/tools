"""
The ModuleCreate class handles generating of module templates
"""

from __future__ import print_function

import logging
import os

import questionary
import rich
import yaml
from packaging.version import parse as parse_version

import nf_core
import nf_core.components.components_create
import nf_core.utils
from nf_core.components.components_command import ComponentCommand

log = logging.getLogger(__name__)


class ModuleCreate(ComponentCommand):
    def __init__(
        self,
        directory=".",
        tool="",
        author=None,
        process_label=None,
        has_meta=None,
        force=False,
        conda_name=None,
        conda_version=None,
    ):
        super().__init__("modules", directory)
        self.directory = directory
        self.tool = tool
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

        modules/modules/nf-core/tool/subtool/
            * main.nf
            * meta.yml
        modules/tests/modules/nf-core/tool/subtool/
            * main.nf
            * test.yml
            * nextflow.config
        tests/config/pytest_modules.yml

        The function will attempt to automatically find a Bioconda package called <tool>
        and matching Docker / Singularity images from BioContainers.
        """

        # Check modules directory structure
        self.check_modules_structure()

        log.info(f"Repository type: [blue]{self.repo_type}")
        if self.directory != ".":
            log.info(f"Base directory: '{self.directory}'")

        log.info(
            "[yellow]Press enter to use default values [cyan bold](shown in brackets)[/] [yellow]or type your own responses. "
            "ctrl+click [link=https://youtu.be/dQw4w9WgXcQ]underlined text[/link] to open links."
        )

        # Collect module info via prompt if empty or invalid
        self.tool, self.subtool = nf_core.components.components_create.collect_name_prompt(
            self.tool, self.component_type
        )

        # Determine the tool name
        self.tool_name = self.tool
        self.tool_dir = self.tool

        if self.subtool:
            self.tool_name = f"{self.tool}/{self.subtool}"
            self.tool_dir = os.path.join(self.tool, self.subtool)

        self.tool_name_underscore = self.tool_name.replace("/", "_")

        # Check existence of directories early for fast-fail
        self.file_paths = nf_core.components.components_create.get_component_dirs(
            self.component_type,
            self.repo_type,
            self.directory,
            self.org,
            self.tool_name,
            self.tool,
            self.subtool,
            self.tool_dir,
            self.force_overwrite,
        )

        # Try to find a bioconda package for 'tool'
        self._get_bioconda_tool()

        # Prompt for GitHub username
        nf_core.components.components_create.get_username(self.author)

        self._get_module_structure_components()

        # Create module template with jinja2
        nf_core.components.components_create.render_template(self.component_type, vars(self), self.file_paths)

        if self.repo_type == "modules":
            # Add entry to pytest_modules.yml
            try:
                with open(os.path.join(self.directory, "tests", "config", "pytest_modules.yml"), "r") as fh:
                    pytest_modules_yml = yaml.safe_load(fh)
                if self.subtool:
                    pytest_modules_yml[self.tool_name] = [
                        f"modules/{self.org}/{self.tool}/{self.subtool}/**",
                        f"tests/modules/{self.org}/{self.tool}/{self.subtool}/**",
                    ]
                else:
                    pytest_modules_yml[self.tool_name] = [
                        f"modules/{self.org}/{self.tool}/**",
                        f"tests/modules/{self.org}/{self.tool}/**",
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
                    anaconda_response = nf_core.utils.anaconda_package(self.tool, ["bioconda"])

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
                    self.bioconda = "bioconda::" + self.tool + "=" + version
                log.info(f"Using Bioconda package: '{self.bioconda}'")
                break
            except (ValueError, LookupError) as e:
                log.warning(
                    f"Could not find Conda dependency using the Anaconda API: '{self.tool_conda_name if self.tool_conda_name else self.tool}'"
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
                        self.tool, version
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
