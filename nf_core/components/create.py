"""
The ComponentCreate class handles generating of module and subworkflow templates
"""

import glob
import json
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

import jinja2
import questionary
import rich
import rich.prompt
import yaml
from packaging.version import parse as parse_version

import nf_core
import nf_core.utils
from nf_core.components.components_command import ComponentCommand
from nf_core.pipelines.lint_utils import run_prettier_on_file

log = logging.getLogger(__name__)


class ComponentCreate(ComponentCommand):
    def __init__(
        self,
        component_type: str,
        directory: Path = Path("."),
        component: str = "",
        author: Optional[str] = None,
        process_label: Optional[str] = None,
        has_meta: Optional[str] = None,
        force: bool = False,
        conda_name: Optional[str] = None,
        conda_version: Optional[str] = None,
        empty_template: bool = False,
        migrate_pytest: bool = False,
        migrate_pytest_hard=False,
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
        self.tool_licence = ""
        self.tool_description = ""
        self.tool_doc_url = ""
        self.tool_dev_url = ""
        self.bioconda = None
        self.singularity_container = None
        self.docker_container = None
        self.file_paths: Dict[str, Path] = {}
        self.not_empty_template = not empty_template
        self.migrate_pytest = migrate_pytest
        self.migrate_pytest_hard = migrate_pytest_hard
        self.pytest_units_str = None
        self.pytest_has_nextflow_config = False

    def create(self) -> bool:
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

        ```tree
        modules/nf-core/tool/subtool/
        ├── main.nf
        ├── meta.yml
        ├── environment.yml
        └── tests
            └── main.nf.test
        ```

        The function will attempt to automatically find a Bioconda package called <component>
        and matching Docker / Singularity images from BioContainers.

        For subworkflows:

        ```tree
        subworkflows/nf-core/tool/subtool/
        ├── main.nf
        ├── meta.yml
        └── tests
            └── main.nf.test
        ```

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
        self.component_dir = Path(self.component)

        if self.subtool:
            self.component_name = f"{self.component}/{self.subtool}"
            self.component_dir = Path(self.component, self.subtool)

        self.component_name_underscore = self.component_name.replace("/", "_")

        # Check existence of directories early for fast-fail
        self.file_paths = self._get_component_dirs()

        if self.migrate_pytest:
            # Rename the component directory to old
            component_old_dir = Path(str(self.component_dir) + "_old")
            component_parent_path = Path(self.directory, self.component_type, self.org)
            component_old_path = component_parent_path / component_old_dir
            component_path = component_parent_path / self.component_dir

            component_path.rename(component_old_path)
        else:
            if self.component_type == "modules":
                # Try to find a bioconda package for 'component'
                self._get_bioconda_tool()

            # Prompt for GitHub username
            self._get_username()

            if self.component_type == "modules":
                self._get_module_structure_components()

        # Add a valid organization name for nf-test tags
        not_alphabet = re.compile(r"[^a-zA-Z]")
        self.org_alphabet = not_alphabet.sub("", self.org)

        # Extract pytest nextflow config
        pytest_nextflow_config_contents = None
        if self.migrate_pytest:
            pytest_nextflow_config_contents = self._extract_nextflow_config()

        # Extract pytest units
        if self.migrate_pytest and self.migrate_pytest_hard:
            self._extract_pytest_units()

        # Create component template with jinja2
        assert self._render_template()
        log.info(f"Created component template: '{self.component_name}'")

        if self.migrate_pytest:
            self._copy_old_files(component_old_path)
            self._copy_nextflow_config(pytest_nextflow_config_contents)
            log.info("Migrate pytest tests: Copied original module files to new module")
            shutil.rmtree(component_old_path)
            self._print_and_delete_pytest_files()

        new_files = [str(path) for path in self.file_paths.values()]

        log.info("Created following files:\n  " + "\n  ".join(new_files))
        return True

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
        process_label_defaults = [
            "process_single",
            "process_low",
            "process_medium",
            "process_high",
            "process_long",
            "process_high_memory",
        ]
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
                "[violet]Will the module require a meta map of sample information?",
                default=True,
            )

    def _render_template(self) -> Optional[bool]:
        """
        Create new module/subworkflow files with Jinja2.
        """
        object_attrs = vars(self)
        # Run jinja2 for each file in the template folder
        env = jinja2.Environment(
            loader=jinja2.PackageLoader("nf_core", f"{self.component_type[:-1]}-template"),
            keep_trailing_newline=True,
        )
        for template_fn, dest_fn in self.file_paths.items():
            log.debug(f"Rendering template file: '{template_fn}'")
            j_template = env.get_template(template_fn)
            object_attrs["nf_core_version"] = nf_core.__version__
            try:
                rendered_output = j_template.render(object_attrs)
            except Exception as e:
                log.error(f"Could not render template file '{template_fn}':\n{e}")
                raise e

            # Write output to the target file
            log.debug(f"Writing output to: '{dest_fn}'")
            dest_fn.parent.mkdir(exist_ok=True, parents=True)
            with open(dest_fn, "w") as fh:
                log.debug(f"Writing output to: '{dest_fn}'")
                fh.write(rendered_output)

            # Mirror file permissions
            template_stat = (
                Path(nf_core.__file__).parent / f"{self.component_type[:-1]}-template" / template_fn
            ).stat()
            dest_fn.chmod(template_stat.st_mode)
        return True

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

    def _get_component_dirs(self) -> Dict[str, Path]:
        """Given a directory and a tool/subtool or subworkflow, set the file paths and check if they already exist

        Returns dict: keys are relative paths to template files, vals are target paths.
        """
        file_paths = {}
        if self.repo_type == "pipeline":
            local_component_dir = Path(self.directory, self.component_type, "local")
            # Check whether component file already exists
            component_file = local_component_dir / f"{self.component_name}.nf"
            if component_file.exists() and not self.force_overwrite:
                raise UserWarning(
                    f"{self.component_type[:-1].title()} file exists already: '{component_file}'. Use '--force' to overwrite"
                )

            if self.component_type == "modules":
                # If a subtool, check if there is a module called the base tool name already
                if self.subtool and (local_component_dir / f"{self.component}.nf").exists():
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
            file_paths["main.nf"] = component_file

        elif self.repo_type == "modules":
            component_dir = Path(self.directory, self.component_type, self.org, self.component_dir)
            # Check if module/subworkflow directories exist already
            if component_dir.exists() and not self.force_overwrite and not self.migrate_pytest:
                raise UserWarning(
                    f"{self.component_type[:-1]} directory exists: '{component_dir}'. Use '--force' to overwrite"
                )

            if self.component_type == "modules":
                # If a subtool, check if there is a module called the base tool name already
                parent_tool_main_nf = Path(
                    self.directory,
                    self.component_type,
                    self.org,
                    self.component,
                    "main.nf",
                )
                if self.subtool and parent_tool_main_nf.exists() and not self.migrate_pytest:
                    raise UserWarning(
                        f"Module '{parent_tool_main_nf}' exists already, cannot make subtool '{self.component_name}'"
                    )

                # If no subtool, check that there isn't already a tool/subtool
                tool_glob = glob.glob(
                    f"{Path(self.directory, self.component_type, self.org, self.component)}/*/main.nf"
                )
                if not self.subtool and tool_glob and not self.migrate_pytest:
                    raise UserWarning(
                        f"Module subtool '{tool_glob[0]}' exists already, cannot make tool '{self.component_name}'"
                    )
            # Set file paths
            # For modules - can be tool/ or tool/subtool/ so can't do in template directory structure
            file_paths["main.nf"] = component_dir / "main.nf"
            file_paths["meta.yml"] = component_dir / "meta.yml"
            if self.component_type == "modules":
                file_paths["environment.yml"] = component_dir / "environment.yml"
            file_paths["tests/main.nf.test.j2"] = component_dir / "tests" / "main.nf.test"
        else:
            raise ValueError("`repo_type` not set correctly")

        return file_paths

    def _get_username(self):
        """
        Prompt for GitHub username
        """
        # Try to guess the current user if `gh` is installed
        author_default = None
        try:
            gh_auth_user = json.loads(subprocess.check_output(["gh", "api", "/user"], stderr=subprocess.DEVNULL))
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

    def _copy_old_files(self, component_old_path):
        """Copy files from old module to new module"""
        log.debug("Copying original main.nf file")
        shutil.copyfile(component_old_path / "main.nf", self.file_paths["main.nf"])
        log.debug("Copying original meta.yml file")
        shutil.copyfile(component_old_path / "meta.yml", self.file_paths["meta.yml"])
        if self.component_type == "modules":
            log.debug("Copying original environment.yml file")
            shutil.copyfile(
                component_old_path / "environment.yml",
                self.file_paths["environment.yml"],
            )
            if (component_old_path / "templates").is_dir():
                log.debug("Copying original templates directory")
                shutil.copytree(
                    component_old_path / "templates",
                    self.file_paths["environment.yml"].parent / "templates",
                )

    def _extract_nextflow_config(self):
        # Create a nextflow.config file if it contains information other than publishDir
        pytest_dir = Path(self.directory, "tests", self.component_type, self.org, self.component_dir)
        nextflow_config = pytest_dir / "nextflow.config"
        if nextflow_config.is_file():
            with open(nextflow_config) as fh:
                config_lines = ""
                for line in fh:
                    if "publishDir" not in line and line.strip() != "":
                        config_lines += line
            # if the nextflow.config file only contained publishDir, non_publish_dir_lines will be 11 characters long (`process {\n}`)
            if len(config_lines) > 11:
                self.pytest_has_nextflow_config = True
                return config_lines

        return None

    def _copy_nextflow_config(self, config_lines):
        if config_lines is None:
            return

        log.debug("Copying nextflow.config file from pytest tests")
        with open(
            Path(
                self.directory,
                self.component_type,
                self.org,
                self.component_dir,
                "tests",
                "nextflow.config",
            ),
            "w+",
        ) as ofh:
            ofh.write(config_lines)

    def _print_and_delete_pytest_files(self):
        """Prompt if pytest files should be deleted and printed to stdout"""
        pytest_dir = Path(self.directory, "tests", self.component_type, self.org, self.component_dir)
        if rich.prompt.Confirm.ask(
            "[violet]Do you want to delete the pytest files?[/]\nPytest file 'main.nf' will be printed to standard output to allow migrating the tests manually to 'main.nf.test'.",
            default=False,
        ):
            with open(pytest_dir / "main.nf") as fh:
                log.info(fh.read())
            if pytest_dir.is_symlink():
                resolved_dir = pytest_dir.resolve()
                log.debug(f"Removing symlink: {resolved_dir}")
                shutil.rmtree(resolved_dir)
                pytest_dir.unlink()
            else:
                shutil.rmtree(pytest_dir)
            log.info(
                "[yellow]Please convert the pytest tests to nf-test in 'main.nf.test'.[/]\n"
                "You can find more information about nf-test [link=https://nf-co.re/docs/contributing/modules#migrating-from-pytest-to-nf-test]at the nf-core web[/link]. "
            )
        else:
            log.info(
                "[yellow]Please migrate the pytest tests to nf-test in 'main.nf.test'.[/]\n"
                "You can find more information about nf-test [link=https://nf-co.re/docs/contributing/modules#migrating-from-pytest-to-nf-test]at the nf-core web[/link].\n"
                f"Once done, make sure to delete the module pytest files to avoid linting errors: {pytest_dir}"
            )
        # Delete tags from pytest_modules.yml
        modules_yml = Path(self.directory, "tests", "config", "pytest_modules.yml")
        with open(modules_yml) as fh:
            yml_file = yaml.safe_load(fh)
        yml_key = str(self.component_dir) if self.component_type == "modules" else f"subworkflows/{self.component_dir}"
        if yml_key in yml_file:
            del yml_file[yml_key]
        with open(modules_yml, "w") as fh:
            yaml.dump(yml_file, fh)
        run_prettier_on_file(modules_yml)

    def _extract_pytest_units(self):
        pytest_dir = Path(self.directory, "tests", self.component_type, self.org, self.component_dir)
        main_nf_contents = Path(pytest_dir, "main.nf").read_text(encoding="UTF-8")

        main_nf_workflows = re.findall(r"workflow\s*(\w+)\s*{([^}]+)}", main_nf_contents, re.DOTALL)

        log.debug(f"Found {len(main_nf_workflows)} workflows {[x[0] for x in main_nf_workflows]}")

        nf_test_workflow = []
        for workflow in main_nf_workflows:
            workflow_name = workflow[0]
            workflow_content = str(workflow[1])

            invoked_components = re.findall(r"(\w+)\s*\(([^\)]+)\)", workflow_content, re.DOTALL)

            invoked_components = [c for c in invoked_components if c[0] != "file"]

            log.debug(f"Found {len(invoked_components)} components invoked by {workflow_name}: {invoked_components}")

            if len(invoked_components) > 1:
                raise ValueError(
                    f"Test workflow {workflow_name} invokes multiple components. This is not supported currently."
                )

            # TODO: Generalize to multiple components
            invoked_component = invoked_components[0]

            invoked_component_name = str(invoked_component[0]).strip()
            invoked_component_args = self._split_pytest_component_args(invoked_component[1].strip())

            arg_data = self._extract_pytest_args_data(
                workflow_name, workflow_content, invoked_component_name, invoked_component_args
            )

            nf_test_workflow.append({"name": workflow_name.replace("_", "-"), "input": arg_data})

        test_units_str = ""
        for test in nf_test_workflow:
            test_name = test["name"]
            log.debug(f"Scaffolding nf-test '{test_name}'")

            input_data_lines = self._make_nf_test_input(test["input"])
            add_stub_option = "options '-stub'" if "stub" in test_name else ""
            test_unit_str = f"""
    test("{test_name}") {{
        {add_stub_option}
        when {{
            process {{
                \"\"\"
                {input_data_lines}
                \"\"\"
            }}
        }}

        then {{
            assertAll(
                {{ assert process.success }},
                {{ assert snapshot(process.out).match() }}
            )
        }}
    }}
    """
            test_units_str += test_unit_str

        self.pytest_units_str = test_units_str

    def _extract_pytest_args_data(
        self, workflow_name, workflow_content, invoked_component_name, invoked_component_args
    ) -> list[str]:
        return [
            self._extract_pytest_arg_data(workflow_name, workflow_content, invoked_component_name, arg)
            for arg in invoked_component_args
        ]

    def _extract_pytest_arg_data(self, workflow_name, workflow_content, invoked_component_name, invoked_component_arg):
        if "[" in invoked_component_arg:
            log.debug(f"Arg '{invoked_component_arg}' is a value")
            return invoked_component_arg

        log.debug(
            f"Looking for arg '{invoked_component_arg}' for '{invoked_component_name}' in workflow '{workflow_name}'"
        )

        re_matches = self._extract_pytest_arg_matches(invoked_component_arg, workflow_content)

        if len(re_matches) != 1:
            raise ValueError(f"'{invoked_component_arg}' data could not be parsed from matches {re_matches}")

        found_arg_data = re_matches[0]

        log.debug(f"For arg '{invoked_component_arg}' found data {found_arg_data}")

        return found_arg_data

    def _extract_pytest_arg_matches(self, invoked_component_arg, workflow_content):
        # multiline list such as input = [etc]
        list_match = re.findall(rf"{invoked_component_arg}\s*=\s*(\[.*?\n\s*\])", workflow_content, re.DOTALL)

        if list_match != []:
            return list_match

        # simple list such as input = [ ]
        list_match = re.findall(rf"{invoked_component_arg}\s*=\s*(\[\s*\])", workflow_content, re.DOTALL)

        if list_match != []:
            return list_match

        # String match such as 'etc', "etc"
        return re.findall(rf"{invoked_component_arg}\s*=\s*(['\"]+.*?['\"]+)", workflow_content, re.DOTALL)

    def _make_nf_test_input(self, input_data):
        input_data_lines = ""
        for index in range(len(input_data)):
            arg_data = input_data[index]
            if "\n" in arg_data:
                input_data_str = self._indent_nf_test_arg(arg_data)
            else:
                input_data_str = arg_data.strip()

            indent = ""
            if index > 0:
                indent = "\t\t\t\t"
            input_data_lines += indent + f"input[{index}] = " + input_data_str + "\n"

        return input_data_lines

    def _indent_nf_test_arg(self, arg_data):
        arg_data_lines = arg_data.split("\n")

        return arg_data_lines[0].strip() + "\n" + "\n".join(["\t\t\t\t" + line.strip() for line in arg_data_lines[1:]])

    def _split_pytest_component_args(self, args_str: str) -> list[str]:
        # Single argument case
        if "," not in args_str:
            return [args_str.strip()]

        args = []

        arg_matches = re.findall(r"(\w+\s*|\[\s*\]|\[\[\],\[\]\])", args_str)

        log.debug(f"For args string {args_str} found matches {arg_matches}")

        for arg_match in arg_matches:
            args.append(str(arg_match).strip())

        return args
