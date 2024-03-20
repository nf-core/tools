from textual import on, work
from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

from nf_core.configs.create.create import (
    ConfigCreate,
)
from nf_core.configs.create.utils import (
    TextInput,
)


class FinalScreen(Screen):
    """A welcome screen for the app."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            """
# Final step
"""
        )
        yield TextInput(
            "savelocation",
            ".",
            "In which directory would you like to save the config?",
            ".",
            classes="row",
        )
        yield Center(Button("Save and close!", id="close_app", variant="success"), classes="cta")

    @work(thread=True, exclusive=True)
    def _create_config(self) -> None:
        """Create the config."""
        create_obj = ConfigCreate(template_config=self.parent.TEMPLATE_CONFIG)
        create_obj.WriteToFile()

    @on(Button.Pressed, "#close_app")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        self._create_config()
        # self.close_app()
