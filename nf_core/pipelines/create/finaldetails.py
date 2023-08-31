"""A Textual app to create a pipeline."""
from textwrap import dedent

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown, Static, Switch

from nf_core.pipelines.create.utils import CreateConfig, TextInput


class FinalDetails(Screen):
    """Name, description, author, etc."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Final details
                """
            )
        )

        yield TextInput(
            "version",
            "Version",
            "First version of the pipeline",
            "1.0dev",
        )
        with Horizontal():
            yield Switch(value=False, id="force")
            yield Static("If the pipeline output directory exists, remove it and continue.", classes="custom_grid")

        yield Center(
            Button("Finish", id="finish", variant="success"),
            classes="cta",
        )

    @on(Button.Pressed, "#finish")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        for text_input in self.query("TextInput"):
            this_input = self.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            version = this_input.value
            if not validation_result.is_valid:
                text_input.query_one(".validation_msg").update("\n".join(validation_result.failure_descriptions))
            else:
                text_input.query_one(".validation_msg").update("")
        try:
            self.parent.TEMPLATE_CONFIG.version = version
        except ValueError:
            pass

        this_switch = self.query_one(Switch)
        try:
            self.parent.TEMPLATE_CONFIG.force = this_switch.value
        except ValueError:
            pass

        self.parent.exit(self.parent.TEMPLATE_CONFIG)
