from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Select

from nf_core.configs.create.utils import ConfigFeature

markdown_intro = """
# What type of infrastructure is the config for?

Different computational infrastructure types require different information.

The current options that are available to you:

- Local: a single laptop/desktop machine, or a single server node with no scheduling system
- HPC: a multi-node server that has a scheduling system such as SLURM, Grid Engine, PBS etc.
"""


class ChooseInfraConfigType(Screen):
    """Choose whether this infrastructure config will be for a local machine or HPC clusters."""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle all button pressed events."""
        if event.button.id == "infratype_continue" and self.query_one("#infra_type").value == "type_hpc":
            self.parent.push_screen("choose_hpcmodules")
        elif event.button.id == "infratype_continue" and self.query_one("#infra_type").value == "type_local":
            self.parent.push_screen("nfcore_details")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)
        yield Center(
            Select([("HPC", "type_hpc"), ("Local", "type_local")], id="infra_type"),
            # Select("local", id="type_local"),
            classes="cta",
        )
        yield Markdown(
            """
# For which type of pipelines will the config be used for?

Configs for nf-core pipelines require extra details to be included in the config.

If you plan to use the config with nf-core configs, please indicate below.
"""
        )
        yield ConfigFeature(
            "",
            "On",
            "Activate to specify config will be used with nf-core pipelines",
            "for_nfcore_pipelines",
            True,
        )
        yield Horizontal(
            Center(
                Button("Back", id="back", variant="default"),
                classes="cta",
            ),
            Center(
                Button("Next", id="infratype_continue", variant="success"),
                classes="cta",
            ),
        )
