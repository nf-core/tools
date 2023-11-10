from textual import on
from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static

markdown = """
# nf-core create

Visualising logging output.
"""


class LoggingScreen(Screen):
    """A screen to show the final logs."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Static(
            f"\n[green]{' ' * 40},--.[grey39]/[green],-."
            + "\n[blue]        ___     __   __   __   ___     [green]/,-._.--~\\"
            + "\n[blue]|\ | |__  __ /  ` /  \ |__) |__      [yellow]   }  {"
            + "\n[blue]   | \| |       \__, \__/ |  \ |___     [green]\`-._,-`-,"
            + "\n[green]                                       `._,._,'\n",
            id="logo",
        )
        yield Markdown(markdown)
        if self.parent.LOGGING_STATE == "repo created":
            yield Center(
                Button("Close App", id="close_app", variant="success"),
                classes="cta",
            )
        else:
            yield Center(
                Button("Close logging screen", id="close_screen", variant="success"),
                classes="cta",
            )
        yield Center(self.parent.LOG_HANDLER.console, classes="cta")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Close the logging screen or the whole app."""
        if event.button.id == "close_app":
            self.parent.exit()
        if event.button.id == "close_screen":
            self.parent.switch_screen("github_repo")
