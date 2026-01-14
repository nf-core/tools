"""Get information about which process/label the user wants to configure."""

from textwrap import dedent

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown

from nf_core.configs.create.utils import (
    ConfigsCreateConfig,
    TextInput,
    init_context
)  ## TODO Move somewhere common?
from nf_core.utils import add_hide_class, remove_hide_class


class DefaultProcess(Screen):
    """Get default process resource requirements."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Default process resources
                """
            )
        )
        yield TextInput(
            "default_process_ncpus",
            "2",
            "Number of CPUs to use by default for all processes.",
            "2",
            classes="column",
        )
        yield TextInput(
            "default_process_memgb",
            "8",
            "Amount of memory in GB to use by default for all processes.",
            "8",
            classes="column",
        )
        yield Markdown("The walltime required by default for all processes.")
        with Horizontal():
            yield TextInput(
                "default_process_hours",
                "1",
                "Hours:",
                "1",
                classes="column",
            )
            yield TextInput(
                "default_process_minutes",
                "0",
                "Minutes:",
                "0",
                classes="column",
            )
            yield TextInput(
                "default_process_seconds",
                "0",
                "Seconds:",
                "0",
                classes="column",
            )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Configure specific processes", id="config_specific_process", variant="success"),
            Button("Finish", id="finish_config", variant="success"),
            classes="cta",
        )

    # Updates the __init__ initialised TEMPLATE_CONFIG object (which is built from the ConfigsCreateConfig class) with the values from the text inputs
    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        new_config = {}
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            new_config[text_input.field_id] = this_input.value
            if not validation_result.is_valid:
                text_input.query_one(".validation_msg").update("\n".join(validation_result.failure_descriptions))
            else:
                text_input.query_one(".validation_msg").update("")
        try:
            with init_context({"is_nfcore": self.parent.NFCORE_CONFIG, "is_infrastructure": self.parent.CONFIG_TYPE == "infrastructure"}):
                # First, validate the new config data
                ConfigsCreateConfig(**new_config)
                # If that passes validation, update the existing config
                self.parent.TEMPLATE_CONFIG = self.parent.TEMPLATE_CONFIG.model_copy(update=new_config)
            if event.button.id == "config_specific_process":
                self.parent.push_screen("custom_process_resources")
            elif event.button.id == "finish_config":
                self.parent.push_screen("final")
        except ValueError:
            pass
