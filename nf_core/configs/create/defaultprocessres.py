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
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    # Updates the __init__ initialised TEMPLATE_CONFIG object (which is built from the ConfigsCreateConfig class) with the values from the text inputs
    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        try:
            if event.button.id == "next":
                self.parent.push_screen("final")
        except ValueError:
            pass
