"""A Textual app to create a pipeline."""
from pydantic import BaseModel, field_validator, Field
import re
from typing import Optional
from textual import on
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Center
from textual.validation import Function, Validator, ValidationResult
from textual.widgets import Button, Footer, Header, Static, Markdown, Input, Pretty
from textwrap import dedent


class CreateConfig(BaseModel):
    """Pydantic model for the nf-core create config."""

    org: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None
    force: Optional[bool] = None
    outdir: Optional[str] = None
    template_yaml: Optional[str] = None
    is_nfcore: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_nospecialchars(cls, v: str) -> str:
        """Check that the pipeline name is simple."""
        if not re.match(r"^[a-z]+$", v):
            raise ValueError("Must be lowercase without punctuation.")
        return v

    @field_validator("org", "description", "author")
    @classmethod
    def notempty(cls, v: str) -> str:
        """Check that string values are not empty."""
        if v.strip() == "":
            raise ValueError("Cannot be left empty.")
        return v


# Initialise as empty
TEMPLATE_CONFIG = CreateConfig()


class TextInput(Static):
    """Widget for text inputs.

    Provides standard interface for a text input with help text
    and validation messages.
    """

    def __init__(self, field_id, placeholder, description, default=None, **kwargs) -> None:
        """Initialise the widget with our values.

        Pass on kwargs upstream for standard usage."""
        super().__init__(**kwargs)
        self.field_id: str = field_id
        self.placeholder: str = placeholder
        self.description: str = description
        self.default: str = default

    def compose(self) -> ComposeResult:
        yield Static(self.description, classes="field_help")
        yield Input(
            placeholder=self.placeholder,
            validators=[ValidateConfig(self.field_id)],
            value=self.default,
        )
        yield Static(classes="validation_msg")

    @on(Input.Changed)
    def show_invalid_reasons(self, event: Input.Changed) -> None:
        """Validate the text input and show errors if invalid."""
        if not event.validation_result.is_valid:
            self.query_one(".validation_msg").update("\n".join(event.validation_result.failure_descriptions))
        else:
            self.query_one(".validation_msg").update("")


class ValidateConfig(Validator):
    """Validate any config value, using Pydantic."""

    def __init__(self, key) -> None:
        """Initialise the validator with the model key to validate."""
        super().__init__()
        self.key = key

    def validate(self, value: str) -> ValidationResult:
        """Try creating a Pydantic object with this key set to this value.

        If it fails, return the error messages."""
        try:
            CreateConfig(**{f"{self.key}": value})
            return self.success()
        except ValueError as e:
            return self.failure(", ".join([err["msg"] for err in e.errors()]))


class WelcomeScreen(Screen):
    """A welcome screen for the app."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Static(
            f"\n[green]{' ' * 40},--.[grey39]/[green],-."
            + "\n[blue]        ___     __   __   __   ___     [green]/,-._.--~\\"
            + "\n[blue]|\ | |__  __ /  ` /  \ |__) |__      [yellow]   }  {"
            + "\n[blue]   | \| |       \__, \__/ |  \ |___     [green]\`-._,-`-,"
            + "\n[green]                                       `._,._,'\n",
            id="logo",
        )
        yield Markdown(
            dedent(
                """
                # nf-core create

                This app will help you create a new nf-core pipeline.
                It uses the nf-core pipeline template, which is kept at
                within the [nf-core/tools repository](https://github.com/nf-core/tools).

                Using this tool is mandatory when making a pipeline that may
                be part of the nf-core community collection at some point.
                However, this tool can also be used to create pipelines that will
                never be part of nf-core. You can still benefit from the community
                best practices for your own workflow.
                """
            )
        )
        yield Center(Button("Let's go!", id="start", variant="success"), classes="cta")


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
            TEMPLATE_CONFIG = CreateConfig(**config)
            self.parent.switch_screen("choose_type")
        except ValueError as e:
            pass


class ChoosePipelineType(Screen):
    """Choose whether this will be an nf-core pipeline or not."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # To nf-core or not to nf-core?

                Next, we need to know what kind of pipeline this will be.

                Choose _"nf-core"_ if:

                * You want your pipeline to be part of the nf-core community
                * You think that there's an outside chance that it ever _could_ be part of nf-core

                Choose _"Custom"_ if:

                * Your pipeline will _never_ be part of nf-core
                * You want full control over *all* features that are included from the template
                    (including those that are mandatory for nf-core).
                """
            )
        )
        yield Center(
            Button("nf-core", id="type_nfcore", variant="success"),
            Button("Custom", id="type_custom", variant="primary"),
            classes="cta",
        )
        yield Markdown(
            dedent(
                """
                ## Not sure? What's the difference?

                Choosing _"nf-core"_ effectively pre-selects the following template features:

                * GitHub Actions Continuous Integration (CI) configuration for the following:
                    * Small-scale (GitHub) and large-scale (AWS) tests
                    * Code format linting with prettier
                    * Auto-fix functionality using @nf-core-bot
                    * Marking old issues as stale
                * Inclusion of shared nf-core config profiles
                """
            )
        )


class PipelineCreateApp(App):
    """A Textual app to manage stopwatches."""

    CSS_PATH = "create.tcss"
    TITLE = "nf-core create"
    SUB_TITLE = "Create a new pipeline with the nf-core pipeline template"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
    ]
    SCREENS = {
        "welcome": WelcomeScreen(),
        "basic_details": BasicDetails(),
        "choose_type": ChoosePipelineType(),
    }

    def on_mount(self) -> None:
        self.push_screen("welcome")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle all button pressed events."""
        if event.button.id == "start":
            self.switch_screen("basic_details")
        elif event.button.id == "type_nfcore":
            self.switch_screen("type_nfcore")
        elif event.button.id == "type_custom":
            self.switch_screen("type_custom")

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark
