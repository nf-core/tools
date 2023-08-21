"""A Textual app to create a pipeline."""
from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Center
from textual.widgets import Button, Footer, Header, Markdown, Input
from textwrap import dedent

from nf_core.pipelines.create.utils import CreateConfig, TextInput


class BasicDetails(Screen):
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
            yield TextInput(
                "org",
                "Organisation",
                "GitHub organisation",
                "nf-core",
                classes="column",
            )
            yield TextInput(
                "name",
                "Pipeline Name",
                "Workflow name",
                classes="column",
            )

        yield TextInput(
            "description",
            "Description",
            "A short description of your pipeline.",
        )
        yield TextInput(
            "author",
            "Author(s)",
            "Name of the main author / authors",
        )
        yield Center(
            Button("Next", variant="success"),
            classes="cta",
        )

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        config = {}
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            this_input.validate(this_input.value)
            config[text_input.field_id] = this_input.value
        try:
            self.parent.TEMPLATE_CONFIG = CreateConfig(**config)
            self.parent.switch_screen("choose_type")
        except ValueError:
            pass
