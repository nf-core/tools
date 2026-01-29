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
        yield TextInput(
            "default_process_hours",
            "1",
            "The default number of hours of walltime required for processes:",
            "1",
            classes="column",
        )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Skip", id="skip", variant="default"),
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    @on(Button.Pressed, "#skip")
    def skip_to_next_screen(self) -> None:
        # Skip to the next screen without saving
        if self.parent.PIPE_CONF_NAMED:
            self.parent.push_screen("multi_named_process_config")
        elif self.parent.PIPE_CONF_LABELLED:
            self.parent.push_screen("multi_labelled_process_config")
        else:
            self.parent.push_screen("final")

    # Updates the __init__ initialised TEMPLATE_CONFIG object (which is built from the ConfigsCreateConfig class) with the values from the text inputs
    @on(Button.Pressed, "#next")
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
            with init_context(self.parent.get_context()):
                # First, validate the new config data
                ConfigsCreateConfig(**new_config)
                # If that passes validation, update the existing config
                self.parent.TEMPLATE_CONFIG = self.parent.TEMPLATE_CONFIG.model_copy(update=new_config)
            # Push the next screen
            if self.parent.PIPE_CONF_NAMED:
                self.parent.push_screen("multi_named_process_config")
            elif self.parent.PIPE_CONF_LABELLED:
                self.parent.push_screen("multi_labelled_process_config")
            else:
                self.parent.push_screen("final")
        except ValueError:
            pass
