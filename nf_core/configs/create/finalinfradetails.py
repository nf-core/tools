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
    ConfigsCreateConfig,
    init_context,
    SUPPORTED_CONTAINERS
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
        self.container_system_list = []
        self.cache_dir = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)
        self.container_system_list = self._get_container_systems()
        self.container_system = self.container_system_list[0] if self.container_system_list else None

        # TODO: convert to dropdown with contents self.container_system_list
        yield TextInput(
            "container_system",
            "Container system",
            "What container or software system will you use to run your pipeline?",
            classes="",
            suggestions=self.container_system_list,
        )
        yield Markdown("## Maximum resources")
        with Horizontal():
            yield TextInput(
                "memory",
                "Memory",
                "Maximum memory (GB) available in your machine.",
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
                "Maximum time (hours) to run your jobs.",
                classes="column",
            )
        with Vertical(id="define-global-cache-dir", classes="hide" if not self.container_system else ""):
            yield Markdown("## Do you want to define a global cache directory for containers or conda environments?")
            yield TextInput(
                "cachedir",
                "/path/to/cache/dir",
                "Define a global cache direcotry.",
                classes="",
                default=self._get_set_directory(f"NXF_{self.container_system.upper()}_CACHEDIR") if self.container_system is not None else "",
            )
        yield TextInput(
            "igenomes_cachedir",
            "iGenomes cache directory",
            "If you have an iGenomes cache directory, specify it.",
            classes="hide" if not self.parent.NFCORE_CONFIG else "",
        )
        yield TextInput(
            "scratch_dir",
            "Scratch directory",
            "If you have to use a specific scratch directory, specify it.",
            classes="",
        )
        with Horizontal(classes="ghrepo-cols"):
            yield Switch(value=False, id="toggle-delete-work")
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
        container_systems = SUPPORTED_CONTAINERS
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
        text_input = self.query_one("#container_system")
        this_input = text_input.query_one(Input)
        self.container_system = this_input.value
        cachedir_text_input = self.query_one("#cachedir")
        cachedir_input = cachedir_text_input.query_one(Input)
        if self.container_system:
            remove_hide_class(self.parent, "define-global-cache-dir")
            if not cachedir_input.value:
                cachedir_path = self._get_set_directory(f"NXF_{self.container_system.upper()}_CACHEDIR")
                cachedir_input.value = cachedir_path or ''
        else:
            add_hide_class(self.parent, "define-global-cache-dir")

    @on(Button.Pressed, "#finish")
    def on_finish_button(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        new_config = {}
        for text_input in self.query("TextInput"):
            if "hide" in text_input.classes:
                continue
            this_input = text_input.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            new_config[text_input.field_id] = this_input.value
            if not validation_result.is_valid:
                text_input.query_one(".validation_msg").update("\n".join(validation_result.failure_descriptions))
            else:
                text_input.query_one(".validation_msg").update("")
        delete_work_switch = self.query_one("#toggle-delete-work")
        new_config['delete_work_dir'] = delete_work_switch.value
        new_config['module'] = self._detect_module_system()
        try:
            with init_context(self.parent.get_context()):
                # First, validate the new config data
                ConfigsCreateConfig(**new_config)
                # If that passes validation, update the existing config
                self.parent.TEMPLATE_CONFIG = self.parent.TEMPLATE_CONFIG.model_copy(update=new_config)
            # Push the next screen
            self.parent.push_screen("final")
        except ValueError:
            pass

    @on(Button.Pressed, "#back")
    def on_back_button(self, event: Button.Pressed) -> None:
        """Clear the default config info"""
        blank_config = {}
        for text_input in self.query("TextInput"):
            if getattr(self.parent.TEMPLATE_CONFIG, text_input.field_id, None):
                blank_config[text_input.field_id] = ''
        try:
            with init_context(self.parent.get_context()):
                # Update the existing config with the blank values
                self.parent.TEMPLATE_CONFIG = self.parent.TEMPLATE_CONFIG.model_copy(update=blank_config)
        except ValueError:
            pass
