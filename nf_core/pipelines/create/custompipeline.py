from textual.app import ComposeResult
from textual.containers import Center, HorizontalScroll, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static, Switch

markdown_genomes = """
Nf-core pipelines are configured to use a copy of the most common reference genome files.

By selecting this option, your pipeline will include a configuration file specifying the paths to these files.

The required code to use these files will also be included in the template.
When the pipeline user provides an appropriate genome key,
the pipeline will automatically download the required reference files.

For more information about reference genomes in nf-core pipelines,
see the [nf-core docs](https://nf-co.re/docs/usage/reference_genomes).
"""

markdown_ci = """
Add Github Continuous Integration tests
"""


class HelpText(Markdown):
    """A class to show a text box with help text."""

    def __init__(self, markdown: str, classes: str) -> None:
        super().__init__(markdown=markdown, classes=classes)

    def show(self) -> None:
        """Method to show the help text box."""
        self.add_class("displayed")

    def hide(self) -> None:
        """Method to hide the help text box."""
        self.remove_class("displayed")


class PipelineFeature(Static):
    """Widget for the selection of pipeline features."""

    def __init__(self, markdown: str, title: str, subtitle: str) -> None:
        self.markdown = markdown
        self.title = title
        self.subtitle = subtitle
        super().__init__()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """When the button is pressed, change the type of the button."""
        if event.button.id == "show_help":
            self.add_class("displayed")
        elif event.button.id == "hide_help":
            self.remove_class("displayed")

    def compose(self) -> ComposeResult:
        """
        Create child widgets.

        Displayed row with a switch, a short text description and a help button.
        Hidden row with a help text box.
        """
        yield HorizontalScroll(
            Switch(value=True),
            Static(self.title, classes="feature_title"),
            Static(self.subtitle, classes="feature_subtitle"),
            Button("Show help", id="show_help", variant="primary"),
            Button("Hide help", id="hide_help"),
            classes="custom_grid",
        )
        yield HelpText(self.markdown, classes="help_box")


class CustomPipeline(Screen):
    """Select if the pipeline will use genomic data."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield ScrollableContainer(
            PipelineFeature(markdown_genomes, "Use reference genomes", "Include reference genome files"),
            PipelineFeature(markdown_ci, "Add Github CI tests", "Include GitHub Continuous Integration (CI) tests"),
        )
        yield Center(
            Button("Done", id="custom_done", variant="success"),
            classes="cta",
        )
