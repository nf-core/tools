from textwrap import dedent

from textual.app import ComposeResult
from textual.containers import Center
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

If you are planning to add a pipeline to the nf-core community, you need to be part of that community!
Please join us on Slack [https://nf-co.re/join](https://nf-co.re/join),
and ask to be added to the GitHub association through the #github-invitations channel.

Come and discuss your plans with the nf-core community as early as possible.
Ideally before you make a start on your pipeline!
These topics are specifically discussed in the [#new-pipelines](https://nfcore.slack.com/channels/new-pipelines) channel.
"""


class WelcomeScreen(Screen):
    """A welcome screen for the app."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Create a pipeline from the nf-core template
                """
            )
        )
        yield Static(
            rf"\n[green]{' ' * 40},--.[grey39]/[green],-."
            + r"\n[blue]        ___     __   __   __   ___     [green]/,-._.--~\\"
            + r"\n[blue]|\ | |__  __ /  ` /  \ |__) |__      [yellow]   }  {"
            + r"\n[blue]   | \| |       \__, \__/ |  \ |___     [green]\`-._,-`-,"
            + r"\n[green]                                       `._,._,'\n",
            id="logo",
        )
        yield Markdown(markdown)
        yield Center(Button("Let's go!", id="start", variant="success"), classes="cta")
