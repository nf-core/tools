import logging
import os
import shutil
from pathlib import Path

import questionary
import yaml
from rich import box
from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import nf_core.modules.module_utils
from nf_core.modules.module_utils import get_repo_type
from nf_core.modules.modules_json import ModulesJson
from nf_core.modules.modules_repo import NF_CORE_MODULES_REMOTE, ModulesRepo

log = logging.getLogger(__name__)


class SubworkflowInfo(object):
    """
    Class to print information of a subworkflow.

    Attributes
    ----------
    meta : YAML object
        stores the information from meta.yml file
    local_path : str
        path of the local subworkflows
    remote_location : str
        remote repository URL
    local : bool
        indicates if the subworkflow is locally installed or not
    repo_type : str
        repository type. Can be either 'pipeline' or 'modules'
    modules_json : ModulesJson object
        contains 'modules.json' file information from a pipeline
    module : str
        name of the tool to get information from

    Methods
    -------
    init_mod_name(subworkflow)
        Makes sure that we have a subworkflow name
    get_subworkflow_info()
        Given the name of a subworkflow, parse meta.yml and print usage help
    get_local_yaml()
        Attempt to get the meta.yml file from a locally installed subworkflow
    get_remote_yaml()
        Attempt to get the meta.yml file from a remote repo
    generate_subworkflow_info_help()
        Take the parsed meta.yml and generate rich help
    """

    def __init__(self, pipeline_dir, tool, remote_url, branch, no_pull):
        # super().__init__(pipeline_dir, remote_url, branch, no_pull)
        self.dir = pipeline_dir
        self.modules_repo = ModulesRepo(remote_url, branch, no_pull)
        try:
            if self.dir:
                self.dir, self.repo_type = nf_core.modules.module_utils.get_repo_type(self.dir)
            else:
                self.repo_type = None
        except LookupError as e:
            raise UserWarning(e)

        self.meta = None
        self.local_path = None
        self.remote_location = None
        self.local = None

        # Quietly check if this is a pipeline or not
        if pipeline_dir:
            try:
                pipeline_dir, repo_type = get_repo_type(pipeline_dir, use_prompt=False)
                log.debug(f"Found {repo_type} repo: {pipeline_dir}")
            except UserWarning as e:
                log.debug(f"Only showing remote info: {e}")
                pipeline_dir = None

        if self.repo_type == "pipeline":
            # # Check modules directory structure
            # self.check_modules_structure()
            # Check modules.json up to date
            self.modules_json = ModulesJson(self.dir)
            self.modules_json.check_up_to_date()
        else:
            self.modules_json = None
        self.module = self.init_mod_name(tool)

    def init_mod_name(self, subworkflow):
        """
        Makes sure that we have a subworkflow name before proceeding.

        Args:
            module: str: Subworkflow name to check
        """
        if subworkflow is None:
            self.local = questionary.confirm(
                "Is the subworkflow locally installed?", style=nf_core.utils.nfcore_question_style
            ).unsafe_ask()
            if self.local:
                if self.repo_type == "modules":
                    subworkflows = self.get_subworkflows_clone_modules()
                else:
                    subworkflows = self.modules_json.get_installed_subworkflows().get(self.modules_repo.remote_url)
                    subworkflows = [module if dir == "nf-core" else f"{dir}/{module}" for dir, module in subworkflows]
                    if subworkflows is None:
                        raise UserWarning(f"No subworkflow installed from '{self.modules_repo.remote_url}'")
            else:
                subworkflows = self.modules_repo.get_avail_subworkflows()
            subworkflow = questionary.autocomplete(
                "Please select a subworkflow", choices=subworkflows, style=nf_core.utils.nfcore_question_style
            ).unsafe_ask()
            while subworkflow not in subworkflows:
                log.info(f"'{subworkflow}' is not a valid subworkflow name")
                subworkflow = questionary.autocomplete(
                    "Please select a new subworkflow", choices=subworkflows, style=nf_core.utils.nfcore_question_style
                ).unsafe_ask()

        return subworkflow

    def get_subworkflow_info(self):
        """Given the name of a subworkflow, parse meta.yml and print usage help."""

        # Running with a local install, try to find the local meta
        if self.local:
            self.meta = self.get_local_yaml()

        # Either failed locally or in remote mode
        if not self.meta:
            self.meta = self.get_remote_yaml()

        # Could not find the meta
        if self.meta is False:
            raise UserWarning(f"Could not find subworkflow '{self.module}'")

        return self.generate_subworkflow_info_help()

    def get_local_yaml(self):
        """Attempt to get the meta.yml file from a locally installed module.

        Returns:
            dict or bool: Parsed meta.yml found, False otherwise
        """

        if self.repo_type == "pipeline":
            # Try to find and load the meta.yml file
            repo_name = self.modules_repo.repo_path
            module_base_path = os.path.join(self.dir, "subworkflows")
            # Check that we have any modules installed from this repo
            modules = self.modules_json.get_installed_subworkflows().get(self.modules_repo.remote_url)
            module_names = [module for _, module in modules]
            if modules is None:
                raise LookupError(f"No modules installed from {self.modules_repo.remote_url}")

            if self.module in module_names:
                install_dir = [dir for dir, module in modules if module == self.module][0]
                mod_dir = os.path.join(module_base_path, install_dir, self.module)
                meta_fn = os.path.join(mod_dir, "meta.yml")
                if os.path.exists(meta_fn):
                    log.debug(f"Found local file: {meta_fn}")
                    with open(meta_fn, "r") as fh:
                        self.local_path = mod_dir
                        return yaml.safe_load(fh)

            log.debug(f"Subworkflow '{self.module}' meta.yml not found locally")
        else:
            module_base_path = os.path.join(self.dir, "subworkflows", "nf-core")
            if self.module in os.listdir(module_base_path):
                mod_dir = os.path.join(module_base_path, self.module)
                meta_fn = os.path.join(mod_dir, "meta.yml")
                if os.path.exists(meta_fn):
                    log.debug(f"Found local file: {meta_fn}")
                    with open(meta_fn, "r") as fh:
                        self.local_path = mod_dir
                        return yaml.safe_load(fh)
            log.debug(f"Subworkflow '{self.module}' meta.yml not found locally")

        return None

    def get_remote_yaml(self):
        """Attempt to get the meta.yml file from a remote repo.

        Returns:
            dict or bool: Parsed meta.yml found, False otherwise
        """
        # Check if our requested module is there
        if self.module not in self.modules_repo.get_avail_subworkflows():
            return False

        file_contents = self.modules_repo.get_subworkflow_meta_yml(self.module)
        if file_contents is None:
            return False
        self.remote_location = self.modules_repo.remote_url
        return yaml.safe_load(file_contents)

    def generate_subworkflow_info_help(self):
        """Take the parsed meta.yml and generate rich help.

        Returns:
            rich renderable
        """

        renderables = []

        # Intro panel
        intro_text = Text()
        if self.local_path:
            intro_text.append(Text.from_markup(f"Location: [blue]{self.local_path}\n"))
        elif self.remote_location:
            intro_text.append(
                Text.from_markup(
                    ":globe_with_meridians: Repository: "
                    f"{ '[link={self.remote_location}]' if self.remote_location.startswith('http') else ''}"
                    f"{self.remote_location}"
                    f"{'[/link]' if self.remote_location.startswith('http') else '' }"
                    "\n"
                )
            )

        if self.meta.get("tools"):
            tools_strings = []
            for tool in self.meta["tools"]:
                for tool_name, tool_meta in tool.items():
                    if "homepage" in tool_meta:
                        tools_strings.append(f"[link={tool_meta['homepage']}]{tool_name}[/link]")
                    else:
                        tools_strings.append(f"{tool_name}")
            intro_text.append(Text.from_markup(f":wrench: Tools: {', '.join(tools_strings)}\n", style="dim"))

        if self.meta.get("description"):
            intro_text.append(Text.from_markup(f":book: Description: {self.meta['description']}", style="dim"))

        renderables.append(
            Panel(
                intro_text,
                title=f"[bold]Subworkflow: [green]{self.module}\n",
                title_align="left",
            )
        )

        # Inputs
        if self.meta.get("input"):
            inputs_table = Table(expand=True, show_lines=True, box=box.MINIMAL_HEAVY_HEAD, padding=0)
            inputs_table.add_column(":inbox_tray: Inputs")
            inputs_table.add_column("Description")
            inputs_table.add_column("Pattern", justify="right", style="green")
            for input in self.meta["input"]:
                for key, info in input.items():
                    inputs_table.add_row(
                        f"[orange1 on black] {key} [/][dim i] ({info['type']})",
                        Markdown(info["description"] if info["description"] else ""),
                        info.get("pattern", ""),
                    )

            renderables.append(inputs_table)

        # Outputs
        if self.meta.get("output"):
            outputs_table = Table(expand=True, show_lines=True, box=box.MINIMAL_HEAVY_HEAD, padding=0)
            outputs_table.add_column(":outbox_tray: Outputs")
            outputs_table.add_column("Description")
            outputs_table.add_column("Pattern", justify="right", style="green")
            for output in self.meta["output"]:
                for key, info in output.items():
                    outputs_table.add_row(
                        f"[orange1 on black] {key} [/][dim i] ({info['type']})",
                        Markdown(info["description"] if info["description"] else ""),
                        info.get("pattern", ""),
                    )

            renderables.append(outputs_table)

        # Installation command
        if self.remote_location:
            cmd_base = "nf-core modules"
            if self.remote_location != NF_CORE_MODULES_REMOTE:
                cmd_base = f"nf-core modules --git-remote {self.remote_location}"
            renderables.append(
                Text.from_markup(f"\n :computer:  Installation command: [magenta]{cmd_base} install {self.module}\n")
            )

        return Group(*renderables)

    # def check_modules_structure(self):
    #     """
    #     Check that the structure of the modules directory in a pipeline is the correct one:
    #         modules/nf-core/TOOL/SUBTOOL

    #     Prior to nf-core/tools release 2.6 the directory structure had an additional level of nesting:
    #         modules/nf-core/modules/TOOL/SUBTOOL
    #     """
    #     if self.repo_type == "pipeline":
    #         wrong_location_modules = []
    #         for directory, _, files in os.walk(Path(self.dir, "modules")):
    #             if "main.nf" in files:
    #                 module_path = Path(directory).relative_to(Path(self.dir, "modules"))
    #                 parts = module_path.parts
    #                 # Check that there are modules installed directly under the 'modules' directory
    #                 if parts[1] == "modules":
    #                     wrong_location_modules.append(module_path)
    #         # If there are modules installed in the wrong location
    #         if len(wrong_location_modules) > 0:
    #             log.info("The modules folder structure is outdated. Reinstalling modules.")
    #             # Remove the local copy of the modules repository
    #             log.info(f"Updating '{self.modules_repo.local_repo_dir}'")
    #             self.modules_repo.setup_local_repo(
    #                 self.modules_repo.remote_url, self.modules_repo.branch, self.hide_progress
    #             )
    #             # Move wrong modules to the right directory
    #             for module in wrong_location_modules:
    #                 modules_dir = Path("modules").resolve()
    #                 correct_dir = Path(modules_dir, self.modules_repo.repo_path, Path(*module.parts[2:]))
    #                 wrong_dir = Path(modules_dir, module)
    #                 shutil.move(wrong_dir, correct_dir)
    #                 log.info(f"Moved {wrong_dir} to {correct_dir}.")
    #             shutil.rmtree(Path(self.dir, "modules", self.modules_repo.repo_path, "modules"))
    #             # Regenerate modules.json file
    #             modules_json = ModulesJson(self.dir)
    #             modules_json.check_up_to_date()

    def get_subworkflows_clone_modules(self):
        """
        Get the subworkflows available in a clone of nf-core/modules
        """
        module_base_path = Path(self.dir, Path("subworkflows", "nf-core"))
        return [
            str(Path(dir).relative_to(module_base_path))
            for dir, _, files in os.walk(module_base_path)
            if "main.nf" in files
        ]
