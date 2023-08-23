from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
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

    def __init__(self, markdown: str, classes: str, id: str) -> None:
        super().__init__(markdown=markdown, classes=classes, id=id)

    def show(self) -> None:
        """Method to show the help text box."""
        self.add_class("displayed")

    def hide(self) -> None:
        """Method to hide the help text box."""
        self.remove_class("displayed")


class CustomPipeline(Screen):
    """Select if the pipeline will use genomic data."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Horizontal(
            Switch(value=True),
            Static("Use reference genomes"),
            Button("Show help", id="show_help", name="genomes", variant="primary"),
            Button("Hide help", id="hide_help", name="genomes"),
            classes="custom_grid",
        )
        yield HelpText(markdown_genomes, classes="help_box", id="genomes")

        yield Horizontal(
            Switch(value=True),
            Static("Include GitHub Continuous Integration (CI) tests"),
            Button("Show help", id="show_help", name="ci", variant="primary"),
            Button("Hide help", id="hide_help", name="ci"),
            classes="custom_grid",
        )
        yield HelpText(markdown_ci, classes="help_box", id="ci")

        yield Center(
            Button("Done", id="done", variant="success"),
            classes="cta",
        )

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save answer to the config."""
        help_text = self.query_one(f"#{event.button.name}", HelpText)
        if event.button.id == "show_help":
            help_text.show()
            self.add_class("displayed")
        elif event.button.id == "hide_help":
            help_text.hide()
            self.remove_class("displayed")
        elif event.button.id == "done":
            pass
