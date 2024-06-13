from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

markdown_intro = """
# Infrastructure or pipelines?

Next, we need to know what kind of config this will be.

Choose _"infrastructure"_ if:

* You want your config to apply to _any_ nextflow or nf-core pipeline
* The config should just set maximum resources, schedulers, containers etc.

Choose _"pipeline"_ if:

* You want your config to tweak pipeline specific resources
"""

markdown_details = """
## Not sure what to pick?

If you want to use the config for many users, or on a HPC, your best bet is to start with an infrastructure config.

If you want to use the config for yourself on your laptop, or adjust a specific pipeline run, choose pipeline.
"""


class ChooseConfigsType(Screen):
    """Choose whether this will be an infrastructure or pipeline config."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)
        yield Center(
            Button("infrastructure", id="type_infrastructure", variant="success"),
            Button("pipeline", id="type_pipeline", variant="primary"),
            classes="cta",
        )
        yield Markdown(markdown_details)
