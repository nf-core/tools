from textual.app import ComposeResult
from textual.containers import Center, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static

markdown = """
# nf-core create

This app will help you create a new nf-core pipeline.
It uses the nf-core pipeline template, which is kept
within the [nf-core/tools repository](https://github.com/nf-core/tools).

Using this tool is mandatory when making a pipeline that may
be part of the nf-core community collection at some point.
However, this tool can also be used to create pipelines that will
never be part of nf-core. You can still benefit from the community
best practices for your own workflow.
"""


class WelcomeScreen(Screen):
    """A welcome screen for the app."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Horizontal():
            with VerticalScroll():
                yield Static(
                    f"\n[green]{' ' * 40},--.[grey39]/[green],-."
                    + "\n[blue]        ___     __   __   __   ___     [green]/,-._.--~\\"
                    + "\n[blue]|\ | |__  __ /  ` /  \ |__) |__      [yellow]   }  {"
                    + "\n[blue]   | \| |       \__, \__/ |  \ |___     [green]\`-._,-`-,"
                    + "\n[green]                                       `._,._,'\n",
                    id="logo",
                )
                yield Markdown(markdown)
                yield Center(Button("Let's go!", id="start", variant="success"), classes="cta")
            yield Center(self.parent.LOG_HANDLER.console, classes="cta log")
