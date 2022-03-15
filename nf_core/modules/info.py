import base64
import logging
import os
import requests
import yaml

from rich import box
from rich.text import Text
from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .modules_command import ModuleCommand
from .module_utils import get_repo_type, get_installed_modules, get_module_git_log, module_exist_in_repo
from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)


class ModuleInfo(ModuleCommand):
    def __init__(self, pipeline_dir, tool):

        self.module = tool
        self.meta = None
        self.local_path = None
        self.remote_location = None

        # Quietly check if this is a pipeline or not
        if pipeline_dir:
            try:
                pipeline_dir, repo_type = get_repo_type(pipeline_dir, use_prompt=False)
                log.debug(f"Found {repo_type} repo: {pipeline_dir}")
            except UserWarning as e:
                log.debug(f"Only showing remote info: {e}")
                pipeline_dir = None

        super().__init__(pipeline_dir)

    def get_module_info(self):
        """Given the name of a module, parse meta.yml and print usage help."""

        # Running with a local install, try to find the local meta
        if self.dir:
            self.meta = self.get_local_yaml()

        # Either failed locally or in remote mode
        if not self.meta:
            self.meta = self.get_remote_yaml()

        # Could not find the meta
        if self.meta == False:
            raise UserWarning(f"Could not find module '{self.module}'")

        return self.generate_module_info_help()

    def get_local_yaml(self):
        """Attempt to get the meta.yml file from a locally installed module.

        Returns:
            dict or bool: Parsed meta.yml found, False otherwise
        """

        # Get installed modules
        self.get_pipeline_modules()

        # Try to find and load the meta.yml file
        module_base_path = f"{self.dir}/modules/"
        if self.repo_type == "modules":
            module_base_path = f"{self.dir}/"
        for dir, mods in self.module_names.items():
            for mod in mods:
                if mod == self.module:
                    mod_dir = os.path.join(module_base_path, dir, mod)
                    meta_fn = os.path.join(mod_dir, "meta.yml")
                    if os.path.exists(meta_fn):
                        log.debug(f"Found local file: {meta_fn}")
                        with open(meta_fn, "r") as fh:
                            self.local_path = mod_dir
                            return yaml.safe_load(fh)

        log.debug(f"Module '{self.module}' meta.yml not found locally")
        return False

    def get_remote_yaml(self):
        """Attempt to get the meta.yml file from a remote repo.

        Returns:
            dict or bool: Parsed meta.yml found, False otherwise
        """
        # Fetch the remote repo information
        self.modules_repo.get_modules_file_tree()

        # Check if our requested module is there
        if self.module not in self.modules_repo.modules_avail_module_names:
            return False

        # Get the remote path
        meta_url = None
        for file_dict in self.modules_repo.modules_file_tree:
            if file_dict.get("path") == f"modules/{self.module}/meta.yml":
                meta_url = file_dict.get("url")

        if not meta_url:
            return False

        # Download and parse
        log.debug(f"Attempting to fetch {meta_url}")
        response = requests.get(meta_url)
        result = response.json()
        file_contents = base64.b64decode(result["content"])
        self.remote_location = self.modules_repo.name
        return yaml.safe_load(file_contents)

    def generate_module_info_help(self):
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
                    f":globe_with_meridians: Repository: [link=https://github.com/{self.remote_location}]{self.remote_location}[/]\n"
                )
            )

        if self.meta.get("tools"):
            tools_strings = []
            for tool in self.meta["tools"]:
                for tool_name, tool_meta in tool.items():
                    tools_strings.append(f"[link={tool_meta['homepage']}]{tool_name}")
            intro_text.append(Text.from_markup(f":wrench: Tools: {', '.join(tools_strings)}\n", style="dim"))

        if self.meta.get("description"):
            intro_text.append(Text.from_markup(f":book: Description: {self.meta['description']}", style="dim"))

        renderables.append(
            Panel(
                intro_text,
                title=f"[bold]Module: [green]{self.module}\n",
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
            if self.remote_location != "nf-core/modules":
                cmd_base = f"nf-core modules --github-repository {self.remote_location}"
            renderables.append(
                Text.from_markup(f"\n :computer:  Installation command: [magenta]{cmd_base} install {self.module}\n")
            )

        return Group(*renderables)
