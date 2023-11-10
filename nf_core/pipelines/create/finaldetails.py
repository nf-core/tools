"""A Textual app to create a pipeline."""
from textwrap import dedent

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown, Static, Switch

from nf_core.pipelines.create.create import PipelineCreate
from nf_core.pipelines.create.loggingscreen import LoggingScreen
from nf_core.pipelines.create.utils import TextInput


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

        with Horizontal():
            yield TextInput(
                "version",
                "Version",
                "First version of the pipeline",
                "1.0dev",
                classes="column",
            )
            yield TextInput(
                "outdir",
                "Output directory",
                "Path to the output directory where the pipeline will be created",
                ".",
                classes="column",
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
        new_config = {}
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            new_config[text_input.field_id] = this_input.value
            if not validation_result.is_valid:
                text_input.query_one(".validation_msg").update("\n".join(validation_result.failure_descriptions))
            else:
                text_input.query_one(".validation_msg").update("")
        try:
            self.parent.TEMPLATE_CONFIG.__dict__.update(new_config)
        except ValueError:
            pass

        this_switch = self.query_one(Switch)
        try:
            self.parent.TEMPLATE_CONFIG.__dict__.update({"force": this_switch.value})
        except ValueError:
            pass

        # Create the new pipeline
        create_obj = PipelineCreate(template_config=self.parent.TEMPLATE_CONFIG)
        create_obj.init_pipeline()
        self.parent.LOGGING_STATE = "pipeline created"
        self.parent.switch_screen(LoggingScreen())
