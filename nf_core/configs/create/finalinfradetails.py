import os
import subprocess

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown, Select, Static, Switch

from nf_core.configs.create.utils import SUPPORTED_CONTAINERS, ConfigsCreateConfig, TextInput, init_context
from nf_core.configs.create.utils import add_hide_class, remove_hide_class

markdown_intro = """
# Configure the options for your infrastructure config
"""

markdown_max_resources = """
## Set maximum available resources

The following fields let you set the maximum available resrouces
on your infrastructure.

Memory, CPUs, and time must be filled out and all processes run with this
configuration will be capped at these values.

The queue size, poll interval, and submit rate fields are optional, since
Nextflow has built-in defaults for these values. Consult the Nextflow
documentation for further details on these default values.
"""

markdown_global_dirs = """
## Define global directories

The following fields let you define global directories for
a container/conda image cache, an iGenomes cache, and
a scratch directory in which to run your jobs.

Each field is optional, but must contain the **full (absolute) path** to
these directories if specified. They may also contain references to
environment variables (e.g. `$CACHEDIR`) and may use the `~` symbol to
refer to your home directory.
"""


class FinalInfraDetails(Screen):
    """Customise the options to create a config for an infrastructure."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.container_system = self._get_container_system()
        self.container_system_list = SUPPORTED_CONTAINERS
        self.cache_dirs = {
            self.container_system: self._get_container_cache_directory(),
        }

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)

        yield Markdown("Select the container/software management system available on your infrastructure.")
        yield Select(
            [(c, c) for c in self.container_system_list],
            prompt="Select container/software management system",
            id="container_system",
            value=self.container_system,
        )
        yield Markdown(markdown_max_resources)
        with Horizontal():
            yield TextInput(
                "memory",
                "Memory",
                "Maximum memory (GB) available on your infrastructure (across all nodes).",
                classes="column",
            )
            yield TextInput(
                "cpus",
                "CPUs",
                "Maximum number of CPUs available on your infrastructure (across all nodes).",
                classes="column",
            )
            yield TextInput(
                "time",
                "Time",
                "Maximum time (hours) available to jobs on your infrastructure (across all nodes).",
                classes="column",
            )
        with Horizontal():
            yield TextInput(
                "queue_size",
                "Queue size",
                "Maximum number of jobs that can be submitted simultaneously on your infrastructure (optional).",
                classes="column",
            )
            yield TextInput(
                "poll_interval",
                "Poll interval",
                "How often (in minutes) to check for successful process completion (optional).",
                classes="column",
            )
            yield TextInput(
                "submit_rate",
                "Jobs per minutes",
                "Maximum number of jobs that can be submitted per minute (optional).",
                classes="column",
            )
        yield Markdown(markdown_global_dirs)
        yield TextInput(
            "cachedir",
            "/path/to/cache/dir",
            "If you have a global container/conda cache directory, specify the **full path** here.",
            classes="",
            default=self._get_container_cache_directory(),
        )
        yield TextInput(
            "igenomes_cachedir",
            "iGenomes cache directory",
            "If you have an iGenomes cache directory, specify the **full path** here.",
            classes="hide" if not self.parent.NFCORE_CONFIG else "",
        )
        yield TextInput(
            "scratch_dir",
            "Scratch directory",
            "If you want your jobs to run within a scratch directory, specify the full path here.",
            classes="",
        )
        with Horizontal(classes="ghrepo-cols"):
            yield Switch(value=False, id="toggle-delete-work")
            with Vertical():
                yield Static("Clean up work directory", classes="")
                yield Markdown(
                    "Select if you want to delete the files in the `work/` directory on successful completion of a run (**prevents `resume` functionality**).",
                    classes="feature_subtitle",
                )
        yield TextInput(
            "retries",
            "Number of retries",
            "Specify the number of retries for a failed job.",
            default="1",
            classes="",
        )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Finish", id="finish", variant="success"),
            classes="cta",
        )

    def _get_container_system(self) -> str:
        """Get the default container system to use for software handling."""
        module_system_used = self._detect_module_system()
        container_systems = SUPPORTED_CONTAINERS
        for system in container_systems:
            # First, see if the container system is available natively
            try:
                output = subprocess.check_output([system], stderr=subprocess.STDOUT).decode("utf-8")
                if output:
                    return system
            except FileNotFoundError:
                pass
            except subprocess.CalledProcessError:
                pass
            # If not available natively, check if module exists
            if module_system_used:
                try:
                    output = subprocess.check_output(["module", "avail", "|", "grep", system], stderr=subprocess.STDOUT).decode("utf-8")
                    if output:
                        return system
                except subprocess.CalledProcessError:
                    pass
        # Return the first supported container by default
        return container_systems[0]

    def _detect_module_system(self) -> bool:
        """Detect if a module system is used"""
        try:
            subprocess.check_output(["module", "--version"])
        except FileNotFoundError:
            return False
        except subprocess.CalledProcessError:
            return False
        return True

    def _get_set_directory(self, dir: str) -> str | None:
        """Get the available cache directories"""
        if dir:
            set_dir = os.environ.get(dir)
            if set_dir:
                return set_dir
        return None

    def _get_container_cache_directory(self) -> str:
        """Try to get the cache directory for the current container system."""
        if not self.container_system:
            return ""
        cachedir_path = self._get_set_directory(f"NXF_{self.container_system.upper()}_CACHEDIR")
        return cachedir_path or ""

    def get_container_cache_directory(self) -> str:
        """Look up the cache directory for the current container system."""
        if not self.container_system:
            return ""
        if not self.cache_dirs.get(self.container_system, None):
            self.cache_dirs[self.container_system] = self._get_container_cache_directory()
        return self.cache_dirs[self.container_system]

    @on(Input.Changed)
    @on(Input.Submitted)
    def set_cache_directory(self) -> None:
        """Set the container system cache dir value"""
        if not self.container_system:
            return None
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            if text_input.field_id == "cachedir":
                cachedir_path = str(this_input.value)
                self.cache_dirs[self.container_system] = cachedir_path

    @on(Select.Changed, "#container_system")
    def get_container_system(self, event: Select.Changed) -> None:
        """Get the container system from dropdown."""
        self.container_system = str(event.value)
        cachedir_text_input = self.query_one("#cachedir")
        cachedir_input = cachedir_text_input.query_one(Input)
        if self.container_system:
            cachedir_input.value = self.get_container_cache_directory()

    @on(Button.Pressed, "#finish")
    def on_finish_button(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        new_config = {}

        # collect dropdown value
        select = self.query_one("#container_system", Select)
        new_config["container_system"] = select.value

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

        # collect switch value
        delete_work_switch = self.query_one("#toggle-delete-work")
        new_config["delete_work_dir"] = delete_work_switch.value
        new_config["module"] = self._detect_module_system()

        # Validate and update the config
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
                blank_config[text_input.field_id] = ""
        try:
            with init_context(self.parent.get_context()):
                # Update the existing config with the blank values
                self.parent.TEMPLATE_CONFIG = self.parent.TEMPLATE_CONFIG.model_copy(update=blank_config)
        except ValueError:
            pass
