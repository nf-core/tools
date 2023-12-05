"""A Textual app to create a pipeline."""
from textwrap import dedent

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown

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
                disabled=self.parent.PIPELINE_TYPE == "nfcore",
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
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        config = {}
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            config[text_input.field_id] = this_input.value
            if not validation_result.is_valid:
                text_input.query_one(".validation_msg").update("\n".join(validation_result.failure_descriptions))
            else:
                text_input.query_one(".validation_msg").update("")
        try:
            self.parent.TEMPLATE_CONFIG = CreateConfig(**config)
            if self.parent.PIPELINE_TYPE == "nfcore":
                self.parent.switch_screen("type_nfcore")
            elif self.parent.PIPELINE_TYPE == "custom":
                self.parent.switch_screen("type_custom")
        except ValueError:
            pass
