from textwrap import dedent

from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static

from nf_core.utils import nfcore_logo


class LoggingScreen(Screen):
    """A screen to show the final logs."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Logging
                """
            )
        )
        yield Static(
            "\n" + "\n".join(nfcore_logo) + "\n",
            id="logo",
        )
        yield Markdown("Creating pipeline..")
        yield Center(self.parent.LOG_HANDLER.console)
        if self.parent.LOGGING_STATE == "repo created":
            yield Center(
                Button("Close App", id="close_app", variant="success"),
                classes="cta",
            )
        else:
            yield Center(
                Button("Continue", id="close_screen", variant="success", disabled=True),
                classes="cta",
            )
