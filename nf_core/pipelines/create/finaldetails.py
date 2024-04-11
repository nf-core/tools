"""A Textual app to create a pipeline."""

from textwrap import dedent

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown, Static, Switch

from nf_core.pipelines.create.create import PipelineCreate
from nf_core.pipelines.create.loggingscreen import LoggingScreen
from nf_core.pipelines.create.utils import ShowLogs, TextInput, add_hide_class, change_select_disabled


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
                "1.0.0dev",
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
            with Vertical():
                yield Static("Force creation", classes="custom_grid")
                yield Static(
                    "Overwrite any existing pipeline output directories.",
                    classes="feature_subtitle",
                )

        yield Center(
            Button("Back", id="back", variant="default"),
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
        self._create_pipeline()
        self.parent.LOGGING_STATE = "pipeline created"
        self.parent.push_screen(LoggingScreen())

    class PipelineExists(Message):
        """Custom message to indicate that the pipeline already exists."""

        pass

    @on(PipelineExists)
    def show_back_button(self) -> None:
        change_select_disabled(self.parent, "back", False)
        add_hide_class(self.parent, "close_screen")

    @work(thread=True, exclusive=True)
    def _create_pipeline(self) -> None:
        """Create the pipeline."""
        self.post_message(ShowLogs())
        create_obj = PipelineCreate(
            template_config=self.parent.TEMPLATE_CONFIG,
            is_interactive=True,
        )
        try:
            create_obj.init_pipeline()
            self.parent.call_from_thread(change_select_disabled, self.parent, "close_screen", False)
            add_hide_class(self.parent, "back")
        except UserWarning:
            self.post_message(self.PipelineExists())
