from textual.app import ComposeResult
from textual.containers import Center, Grid
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

markdown_intro = """
# Is this configuration file part of the nf-core organisation?
"""

markdown_type_nfcore = """
## Choose _"nf-core"_ if:

Infrastructure configs:
* You want to add the configuration file to the nf-core/configs repository.

Pipeline configs:
* The configuration file is for an nf-core pipeline.
"""
markdown_type_custom = """
## Choose _"Custom"_ if:

All configs:
* You want full control over *all* parameters or options in the config
    (including those that are mandatory for nf-core).

Infrastructure configs:
* You will _never_ add the configuration file to the nf-core/configs repository.

Pipeline configs:
* The configuration file is for a custom pipeline which will _never_ be part of nf-core.
"""

markdown_details = """
## What's the difference?

Choosing _"nf-core"_ will make the following of the options mandatory:

Infrastructure configs:
* Providing the name and github handle of the author and contact person.
* Providing a description of the config.
* Providing the URL of the owning institution.
* Setting up `resourceLimits` to set the maximum resources.
"""


class ChooseNfcoreConfig(Screen):
    """Choose whether this will be an nf-core config or not."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)
        yield Grid(
            Center(
                Markdown(markdown_type_nfcore),
                Center(Button("nf-core", id="type_nfcore", variant="success")),
            ),
            Center(
                Markdown(markdown_type_custom),
                Center(Button("Custom", id="type_custom", variant="primary")),
            ),
            classes="col-2 pipeline-type-grid",
        )
        yield Markdown(markdown_details)
