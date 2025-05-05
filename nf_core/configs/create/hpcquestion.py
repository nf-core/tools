from textual.app import ComposeResult
from textual.containers import Center, Grid
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

markdown_intro = """
# Is this configuration file for an HPC config?
"""

markdown_type_hpc = """
## Choose _"HPC"_ if:

You want to create a config file for an HPC.
"""
markdown_type_pc = """
## Choose _"PC"_ if:

You want to create a config file to run your pipeline on a personal computer.
"""

markdown_details = """
## What's the difference?

Choosing _"HPC"_ will add the following configurations:

* Provide a scheduler
* Provide the name of a queue
* Select if a module system is used
* Select if you need to load other modules
"""


class ChooseHpc(Screen):
    """Choose whether this will be a config for an HPC or not."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)
        yield Grid(
            Center(
                Markdown(markdown_type_hpc),
                Center(Button("HPC", id="type_hpc", variant="success")),
            ),
            Center(
                Markdown(markdown_type_pc),
                Center(Button("PC", id="type_pc", variant="primary")),
            ),
            classes="col-2 pipeline-type-grid",
        )
        yield Markdown(markdown_details)
        yield Center(Button("Back", id="back", variant="default"), classes="cta")
