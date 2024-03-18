from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

markdown_intro = """
# What is the location of your infrastructure?

Different computational infrastructure types require different information.

The current options that are available to you:

- Local: a single laptop/desktop machine, or a single server node with no scheduling system
- HPC: a multi-node server that has a scheduling system such as SLURM, Grid Engine, PBS etc.
"""


class ChooseInfraConfigType(Screen):
    """Choose whether this infrastructure config will be for a local machine or HPC clusters."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)
        yield Center(
            Button("hpc", id="type_local", variant="success"),
            Button("local", id="type_hpc", variant="primary"),
            classes="cta",
        )
        yield Center(
            Button("Back", id="back", variant="default"),
            classes="cta",
        )
