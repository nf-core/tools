import os
import subprocess
from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown, Static, Switch

from nf_core.configs.create.utils import (
    TextInput,
)
from nf_core.utils import add_hide_class, remove_hide_class

markdown_intro = """
# Configure the options for your infrastructure config
"""


class FinalInfraDetails(Screen):
    """Customise the options to create a config for an infrastructure."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.container_system = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)
        container_systems = self._get_container_systems()
        yield TextInput(
            "container_system",
            "Container system",
            "What container or software system will you use to run your pipeline?",
            classes="",
            suggestions=container_systems,
        )
        yield Markdown("## Maximum resources")
        with Horizontal():
            yield TextInput(
                "memory",
                "Memory",
                "Maximum memory available in your machine.",
                classes="column",
            )
            yield TextInput(
                "cpus",
                "CPUs",
                "Maximum number of CPUs available in your machine.",
                classes="column",
            )
            yield TextInput(
                "time",
                "Time",
                "Maximum time to run your jobs.",
                classes="column",
            )
        yield Markdown("## Do you want to define a global cache directory for containers or conda environments?")
        with Horizontal():
            yield TextInput(
                "envvar",
                "Nextflow cachedir environment variable",
                "Environment variable to define a global cache directory.",
                classes="",
                default=f"NXF_{self.container_system.upper()}_CACHEDIR" if self.container_system is not None else "",
            )
            yield TextInput(
                "cachedir",
                f"NXF_{self.container_system.upper()}_CACHEDIR" if self.container_system is not None else "",
                "Define a global cache direcotry.",
                classes="",
                default=self._get_set_directory(f"NXF_{self.container_system.upper()}_CACHEDIR")
                if self.container_system is not None
                else "",
            )
        yield TextInput(
            "igenomes_cachedir",
            "iGenomes cache directory",
            "If you have an iGenomes cache direcotry, specify it.",
            classes="hide" if not self.parent.NFCORE_CONFIG else "",
        )
        yield TextInput(
            "scratch_dir",
            "Scratch directory",
            "If you have to use a specific scratch direcotry, specify it.",
            classes="",
        )
        with Horizontal(classes="ghrepo-cols"):
            yield Switch(value=False, id="private")
            with Vertical():
                yield Static("Delete work directory", classes="")
                yield Markdown(
                    "Select if you want to delete the files in the `work/` directory on successful completion of a run.",
                    classes="feature_subtitle",
                )
        yield TextInput(
            "retries",
            "Number of retries",
            "Specify the number of retries for a failed job.",
            classes="",
        )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Finish", id="finish", variant="success"),
            classes="cta",
        )

    def _get_container_systems(self) -> list[str]:
        """Get the available container systems to use for software handling."""
        module_system_used = self._detect_module_system()
        container_systems = ["singularity", "docker", "apptainer", "charliecloud", "podman", "sarus", "shifter"]
        available_systems = []
        if module_system_used:
            for system in container_systems:
                try:
                    output = subprocess.check_output(["module", "avail", "|", "grep", system]).decode("utf-8")
                    if output:
                        available_systems.append(system)
                except subprocess.CalledProcessError:
                    continue
        else:
            for system in container_systems:
                try:
                    output = subprocess.check_output([system]).decode("utf-8")
                    if output:
                        available_systems.append(system)
                except FileNotFoundError:
                    continue
                except subprocess.CalledProcessError:
                    continue
        return available_systems

    def _detect_module_system(self) -> bool:
        """Detect if a module system is used"""
        try:
            subprocess.check_output(["module", "--version"])
        except FileNotFoundError:
            return False
        except subprocess.CalledProcessError:
            return False
        return True

    def _get_set_directory(self, dir: str) -> Optional[str]:
        """Get the available cache directories"""
        if dir:
            set_dir = os.environ.get(dir)
            if set_dir:
                return set_dir
        return None

    @on(Input.Changed)
    def get_container_system(self) -> None:
        """Get the container system from the input."""
        self.container_system = None
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            if text_input.field_id == "container_system":
                self.container_system = this_input.value
        if self.container_system is not None:
            add_hide_class(self.parent, "cachedir")
            add_hide_class(self.parent, "envvar")
        else:
            remove_hide_class(self.parent, "cachedir")
            remove_hide_class(self.parent, "envvar")
