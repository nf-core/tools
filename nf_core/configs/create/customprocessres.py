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
        self.config_stack = []
        self.current_config = {}

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
                classes="column",
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
            Button("Configure another process", id="another"),
            Button("Finish", id="finish_config", variant="success"),
            classes="cta",
        )

    @on(Switch.Changed, "#toggle_process_name_label")
    def on_toggle_process_name_label(self, event: Switch.Changed) -> None:
        """ Handle toggling the process name/label switch """
        self.select_label = event.value
        # Update the switch label
        for label in self.query(Label):
            if label.id == "name_or_label_text":
                label.update("label" if self.select_label else "name")


    # Updates the __init__ initialised TEMPLATE_CONFIG object (which is built from the ConfigsCreateConfig class) with the values from the text inputs
    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        if event.button.id in ["finish_config", "another"]:
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
                with init_context({"is_nfcore": self.parent.NFCORE_CONFIG, "is_infrastructure": self.parent.CONFIG_TYPE == "infrastructure"}):
                    ConfigsCreateConfig(**tmp_config)
                # Add to the config stack
                tmp_config['select_label'] = self.select_label
                self.config_stack.append(tmp_config)
                if event.button.id == "another":
                    # If configuring another process, push a blank config to the config stack
                    # and push a new copy of this screen to the screen stack
                    self.config_stack.append({})
                    self.parent.push_screen("custom_process_resources")
                else:
                    # If finalising the custom resources, add them all to the config now
                    new_config = {}
                    for key in ["labelled_process_resources", "named_process_resources"]:
                        new_config[key] = self.parent.TEMPLATE_CONFIG.__dict__.get(key)
                        if new_config[key] is None:
                            new_config[key] = {}
                    for tmp_config in self.config_stack:
                        select_label = tmp_config['select_label']
                        process_name_or_label = tmp_config.get('custom_process_name')
                        key = "labelled_process_resources" if select_label else "named_process_resources"
                        new_config[key][process_name_or_label] = tmp_config
                    self.parent.TEMPLATE_CONFIG = self.parent.TEMPLATE_CONFIG.model_copy(update=new_config)
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
        # Also reset switch
        switch_input = self.query_one(Switch)
        if 'select_label' in self.current_config:
            self.select_label = self.current_config['select_label']
        else:
            self.select_label = False
        if switch_input.value != self.select_label:
            switch_input.toggle()
