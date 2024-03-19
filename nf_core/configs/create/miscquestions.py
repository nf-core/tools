from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

from nf_core.configs.create.utils import ConfigFeature, TextInputWithHelp

markdown_intro = """
# Miscellaneous questions

This section contains questions that are specify various options that do not fall under the main categories of Nextflow configuration scopes.
"""


class ChooseMiscOptions(Screen):
    """Choose whether this infrastructure config will be for a local machine or HPC clusters."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)
        yield ConfigFeature(
            "",
            "On",
            "Activate automatic clean up of `work/` directories on successful pipeline completion",
            "for_nfcore_pipelines",
            True,
        )
        yield TextInputWithHelp(
            field_id="noretries",
            placeholder="2",
            description="No. of retries Nextflow should attempt to re-run a failed process (with increased resource requests)",
            markdown="TODO",
            default="2",
        )
        yield Horizontal(
            Center(
                Button("Back", id="back", variant="default"),
                classes="cta",
            ),
            Center(
                Button("Next", id="miscquestions_continue", variant="success"),
                classes="cta",
            ),
        )
