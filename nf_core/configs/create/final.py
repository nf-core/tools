from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

from nf_core.pipelines.create.utils import TextInput


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
            "In which location would you like to save the config?",
            ".",
            classes="row",
        )
        yield Center(Button("Save and close!", id="close_app", variant="success"), classes="cta")
