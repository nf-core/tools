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


class PipelineConfigQuestion(Screen):
    """Determine whether the user wants to configure the default resources and/or specific process names/labels."""

    def __init__(self) -> None:
        super().__init__()
        self.config_defaults = False
        self.config_named_processes = False
        self.config_labels = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # What would you like to configure?
                """
            )
        )
        with Horizontal():
            yield Label(
                "Configure default process resources?",
                id="toggle_configure_defaults_label"
            )
            yield Switch(
                id="toggle_configure_defaults",
                value=self.config_defaults,
            )
            yield Label(
                "Yes" if self.config_defaults else "No",
                id="toggle_configure_defaults_state_label"
            )
        with Horizontal():
            yield Label(
                "Configure specific named processes?",
                id="toggle_configure_names_label"
            )
            yield Switch(
                id="toggle_configure_names",
                value=self.config_defaults,
            )
            yield Label(
                "Yes" if self.config_defaults else "No",
                id="toggle_configure_names_state_label"
            )
        with Horizontal():
            yield Label(
                "Configure labels?",
                id="toggle_configure_labels_label"
            )
            yield Switch(
                id="toggle_configure_labels",
                value=self.config_defaults,
            )
            yield Label(
                "Yes" if self.config_defaults else "No",
                id="toggle_configure_labels_state_label"
            )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    @on(Switch.Changed)
    def on_toggle_switch(self, event: Switch.Changed) -> None:
        """ Handle toggling the switches that determine which pipeline resources to configure """
        valid_toggles = {
            'toggle_configure_defaults': 'config_defaults',
            'toggle_configure_names': 'config_named_processes',
            'toggle_configure_labels': 'config_labels',
        }

        if event.switch.id not in valid_toggles:
            return

        attr = valid_toggles[event.switch.id]
        self.__setattr__(attr, event.value)

        # Update the switch label
        for label in self.query(Label):
            if label.id == f'{event.switch.id}_state_label':
                label.update("Yes" if event.value else "No")

    # Updates the __init__ initialised TEMPLATE_CONFIG object (which is built from the ConfigsCreateConfig class) with the values from the text inputs
    @on(Button.Pressed, "#next")
    def on_next_button_pressed(self, event: Button.Pressed) -> None:
        """Save configuration options and then move to the next screen."""
        # Update app tracking variables for whether to configure named and/or labelled processes
        self.parent.PIPE_CONF_NAMED = self.config_named_processes
        self.parent.PIPE_CONF_LABELLED = self.config_labels

        # Proceed to next screen depending on what choices the user has made
        if self.config_defaults:
            self.parent.push_screen("default_process_resources")
        elif self.config_named_processes:
            self.parent.push_screen("named_process_resources")
        elif self.config_labels:
            self.parent.push_screen("labelled_process_resources")
        else:
            self.parent.push_screen("final")
