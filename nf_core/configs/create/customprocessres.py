"""Get information about which process/label the user wants to configure."""

from textwrap import dedent

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown, Switch, Label
from enum import Enum
from nf_core.utils import add_hide_class, remove_hide_class

from nf_core.configs.create.utils import (
    ConfigsCreateConfig,
    TextInput,
    init_context
)  ## TODO Move somewhere common?
from nf_core.utils import add_hide_class, remove_hide_class


class CustomProcess(Screen):
    """Get default process resource requirements."""

    def __init__(self) -> None:
        super().__init__()
        self.select_label = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Custom process resources
                """
            )
        )
        with Horizontal():
            yield TextInput(
                "custom_process_name",
                "",
                "The name of the process you wish to configure.",
                "",
                classes="column hide" if self.select_label else "column",
            )
            yield TextInput(
                "custom_process_label",
                "",
                "The process label you wish to configure.",
                "",
                classes="column hide" if not self.select_label else "column",
            )
        with Horizontal():
            yield Label(
                "Selecting a process by name or label:",
                id="toggle_process_name_label_text"
            )
            yield Switch(
                id="toggle_process_name_label",
                value=self.select_label,
            )
            yield Label(
                "label" if self.select_label else "name",
                id="name_or_label_text"
            )
        yield TextInput(
            "custom_process_ncpus",
            "2",
            "Number of CPUs to use for the process.",
            "2",
            classes="column",
        )
        yield TextInput(
            "custom_process_memgb",
            "8",
            "Amount of memory in GB to use for the process.",
            "8",
            classes="column",
        )
        yield Markdown("The walltime required for the process.")
        with Horizontal():
            yield TextInput(
                "custom_process_hours",
                "1",
                "Hours:",
                "1",
                classes="column",
            )
            yield TextInput(
                "custom_process_minutes",
                "0",
                "Minutes:",
                "0",
                classes="column",
            )
            yield TextInput(
                "custom_process_seconds",
                "0",
                "Seconds:",
                "0",
                classes="column",
            )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    @on(Switch.Changed, "#toggle_process_name_label")
    def on_toggle_process_name_label(self, event: Switch.Changed) -> None:
        """ Handle toggling the process name/label switch """
        self.select_label = event.value
        # Update the input text box and labels
        for text_input in self.query("TextInput"):
            if text_input.field_id in ["custom_process_name", "custom_process_label"]:
                text_input.refresh(repaint=True, layout=True, recompose=True)
        if self.select_label:
            add_hide_class(self.parent, "custom_process_name")
            remove_hide_class(self.parent, "custom_process_label")
        else:
            add_hide_class(self.parent, "custom_process_label")
            remove_hide_class(self.parent, "custom_process_name")
        # Update the switch label as well
        for label in self.query(Label):
            if label.id == "name_or_label_text":
                label.update("label" if self.select_label else "name")


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
            if event.button.id == "next":
                self.parent.push_screen("final")
        except ValueError:
            pass
