from textual import on
from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

markdown_intro = """
## You are now creating a custom pipeline

# Will your pipeline use genomic data?

Nf-core pipelines are configured to use a copy of the most common reference genome files.

By selecting this option, your pipeline will include a configuration file specifying the paths to these files.

The required code to use these files will also be included in the template.
When the pipeline user provides an appropriate genome key,
the pipeline will automatically download the required reference files.

For more information about reference genomes in nf-core pipelines,
see the [nf-core docs](https://nf-co.re/docs/usage/reference_genomes).
"""


class UseGenomicData(Screen):
    """Select if the pipeline will use genomic data."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)
        yield Center(
            Button("Use genomic data", id="true", variant="success"),
            Button("Skip genomic data", id="false", variant="primary"),
            classes="cta",
        )

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save answer to the config."""
        try:
            # TODO
            # self.parent.TEMPLATE_CONFIG.template_yaml["skip"] = [True if event.button.id == "true" else False]
            # self.parent.switch_screen("continuous_integration")
            pass
        except ValueError:
            pass
