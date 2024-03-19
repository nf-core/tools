"""A Textual app to create a pipeline."""

from textwrap import dedent

from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

from nf_core.configs.create.utils import TextInputWithHelp


class ChooseOtherLocations(Screen):
    """Name, description, author, etc."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Basic details
                """
            )
        )
        with Horizontal():
            yield TextInputWithHelp(
                "igenomescache_location",
                "",
                "Location of existing iGenomes cache",
                "Long form help text goes here",
                classes="row",
            )

        yield TextInputWithHelp(
            "scratch_location",
            "",
            "Path of alternative scratch location",
            "Long form help text goes here",
        )

        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Next", id="otherlocations_continue", variant="success"),
            classes="cta",
        )
