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


class NamedProcess(Screen):
    """Get named process resource requirements."""

    def __init__(self) -> None:
        super().__init__()
        self.config_stack = []
        self.current_config = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Custom process resources by name
                """
            )
        )
        yield TextInput(
            "custom_process_name",
            "",
            "The name of the process you wish to configure.",
            "",
            classes="column",
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
        yield TextInput(
            "custom_process_hours",
            "1",
            "The number of hours of walltime required for the process:",
            "1",
            classes="column",
        )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Configure another process", id="another"),
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    # Updates the __init__ initialised TEMPLATE_CONFIG object (which is built from the ConfigsCreateConfig class) with the values from the text inputs
    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        if event.button.id in ["next", "another"]:
            tmp_config = {}
            for text_input in self.query("TextInput"):
                this_input = text_input.query_one(Input)
                validation_result = this_input.validate(this_input.value)
                tmp_config[text_input.field_id] = this_input.value
                if not validation_result.is_valid:
                    text_input.query_one(".validation_msg").update("\n".join(validation_result.failure_descriptions))
                else:
                    text_input.query_one(".validation_msg").update("")
            # Validate the config
            try:
                with init_context(self.parent.get_context()):
                    ConfigsCreateConfig(**tmp_config)
                # Add to the config stack
                self.config_stack.append(tmp_config)
                if event.button.id == "another":
                    # If configuring another process, push a blank config to the config stack
                    # and push a new copy of this screen to the screen stack
                    self.config_stack.append({})
                    self.parent.push_screen("named_process_resources")
                else:
                    # If finalising the custom resources, add them all to the config now
                    key = "named_process_resources"
                    new_config = {key: {}}
                    for tmp_config in self.config_stack:
                        process_name = tmp_config.get('custom_process_name')
                        new_config[key][process_name] = tmp_config
                    self.parent.TEMPLATE_CONFIG = self.parent.TEMPLATE_CONFIG.model_copy(update=new_config)
                    # Push the next screen
                    if self.parent.PIPE_CONF_LABELLED:
                        self.parent.push_screen("labelled_process_resources")
                    else:
                        self.parent.push_screen("final")
            except ValueError:
                pass

    def on_screen_resume(self):
        # Grab the last config in the stack if it exists
        try:
            self.current_config = self.config_stack.pop()
        except IndexError:
            self.current_config = {}
        # Reset all input field values
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            this_input.clear()
            field_id = text_input.field_id
            if field_id in self.current_config:
                this_input.insert(self.current_config[field_id], 0)
            else:
                text_input.refresh(repaint=True, layout=True, recompose=True)
