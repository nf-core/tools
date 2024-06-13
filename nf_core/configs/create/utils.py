import re
from logging import LogRecord
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from rich.logging import RichHandler
from textual import on
from textual._context import active_app
from textual.app import ComposeResult
from textual.containers import HorizontalScroll
from textual.message import Message
from textual.validation import ValidationResult, Validator
from textual.widget import Widget
from textual.widgets import Button, Input, Markdown, RichLog, Static, Switch


class CreateConfig(BaseModel):
    """Pydantic model for the nf-core create config."""

    config_type: Optional[str] = None
    infrastructure_type: Optional[str] = None
    for_nfcore_pipelines: Optional[bool] = None
    use_modules: Optional[bool] = None
    config_name: Optional[str] = None
    config_author: Optional[str] = None
    config_handle: Optional[str] = None
    config_description: Optional[str] = None
    config_url: Optional[str] = None
    containercache_location: Optional[str] = None
    igenomescache_location: Optional[str] = None
    scratch_location: Optional[str] = None
    savelocation: Optional[str] = None
    max_cpus: Optional[str] = None
    max_mem: Optional[str] = None
    max_time: Optional[str] = None
    noretries: Optional[str] = None

    model_config = ConfigDict(extra="allow")

    @field_validator("config_name")
    @classmethod
    def name_nospecialchars(cls, v: str) -> str:
        """Check that the config name is simple."""
        if not re.match(r"^[a-z]+$", v):
            raise ValueError("Must be lowercase without punctuation.")
        return v

    @field_validator("config_handle")
    @classmethod
    def handle_suffix(cls, v: str) -> str:
        """Check that the config author's handle is in handle format ."""
        ## regex taken from: https://github.com/shinnn/github-username-regex
        if not re.match(r"^@[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}$", v):
            raise ValueError(
                "Must be a valid GitHub user handle, starting with @, no punctuation, and max 39 characters."
            )
        return v

    @field_validator("config_url")
    @classmethod
    def valid_url(cls, v: str) -> str:
        """Check that the config institutional URL is valid ."""
        if not re.match(
            r"^https?:\/\/.*",
            v,
        ):
            raise ValueError("Must be a valid URL")
        return v

    @field_validator(
        "containercache_location",
        "igenomescache_location",
        "scratch_location",
        "savelocation",
    )
    @classmethod
    def valid_path(cls, v: str) -> str:
        """Check that a path is valid."""
        if not Path(v).is_dir():
            raise ValueError("Must be a valid absolute path on your filesystem.")
        return v

    @field_validator("max_cpus", "max_mem", "max_time", "noretries")
    @classmethod
    def valid_number(cls, v: str) -> str:
        """Check that a number is valid."""
        if not re.match(r"^[0-9]+$", v):
            raise ValueError("Must be a valid integer number.")
        return v


class TextInput(Static):
    """Widget for text inputs.

    Provides standard interface for a text input with short help text
    and validation messages.
    """

    def __init__(self, field_id, placeholder, description, default=None, password=None, **kwargs) -> None:
        """Initialise the widget with our values.

        Pass on kwargs upstream for standard usage."""
        super().__init__(**kwargs)
        self.field_id: str = field_id
        self.id: str = field_id
        self.placeholder: str = placeholder
        self.description: str = description
        self.default: str = default
        self.password: bool = password

    def compose(self) -> ComposeResult:
        yield Static(self.description, classes="field_help")
        yield Input(
            placeholder=self.placeholder,
            validators=[ValidateConfig(self.field_id)],
            value=self.default,
            password=self.password,
        )
        yield Static(classes="validation_msg")

    @on(Input.Changed)
    @on(Input.Submitted)
    def show_invalid_reasons(self, event: Union[Input.Changed, Input.Submitted]) -> None:
        """Validate the text input and show errors if invalid."""
        if not event.validation_result.is_valid:
            self.query_one(".validation_msg").update("\n".join(event.validation_result.failure_descriptions))
        else:
            self.query_one(".validation_msg").update("")


class TextInputWithHelp(Static):
    """Widget for text inputs.

    Provides standard interface for a text input with short and optional long help text
    and validation messages.
    """

    def __init__(
        self,
        field_id,
        placeholder,
        description,
        markdown,
        default=None,
        password=None,
        **kwargs,
    ) -> None:
        """Initialise the widget with our values.

        Pass on kwargs upstream for standard usage."""
        super().__init__(**kwargs)
        self.field_id: str = field_id
        self.id: str = field_id
        self.placeholder: str = placeholder
        self.description: str = description
        self.markdown = markdown
        self.default: str = default
        self.password: bool = password

    ## Dynamic updating of question contents
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """When the button is pressed, change the type of the button."""
        if event.button.id == "show_help":
            self.add_class("displayed")
        elif event.button.id == "hide_help":
            self.remove_class("displayed")

    ## Define the layout of the question
    def compose(self) -> ComposeResult:
        yield Static(self.description, classes="field_help")
        yield HorizontalScroll(
            Input(
                placeholder=self.placeholder,
                validators=[ValidateConfig(self.field_id)],
                value=self.default,
                password=self.password,
            ),
            Button("Show help", id="show_help", variant="primary"),
            Button("Hide help", id="hide_help"),
            HelpText(markdown=self.markdown, classes="help_box"),
            Static(classes="validation_msg"),
            classes="custom_grid",
        )

    @on(Input.Changed)
    @on(Input.Submitted)
    def show_invalid_reasons(self, event: Union[Input.Changed, Input.Submitted]) -> None:
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
        except ValidationError as e:
            return self.failure(", ".join([err["msg"] for err in e.errors()]))


class HelpText(Markdown):
    """A class to show a text box with help text."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def show(self) -> None:
        """Method to show the help text box."""
        self.add_class("displayed")

    def hide(self) -> None:
        """Method to hide the help text box."""
        self.remove_class("displayed")


class ConfigFeature(Static):
    """Widget for the activation of config features."""

    def __init__(
        self,
        markdown: str,
        title: str,
        subtitle: str,
        field_id: str,
        default=bool,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.markdown = markdown
        self.title = title
        self.subtitle = subtitle
        self.field_id = field_id
        self.default = False

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
            Switch(value=self.default, id=self.field_id),
            Static(self.title, classes="feature_title"),
            Static(self.subtitle, classes="feature_subtitle"),
            Button("Show help", id="show_help", variant="primary"),
            Button("Hide help", id="hide_help"),
            classes="custom_grid",
        )
        yield HelpText(markdown=self.markdown, classes="help_box")


class LoggingConsole(RichLog):
    file = False
    console: Widget

    def print(self, content):
        self.write(content)


class CustomLogHandler(RichHandler):
    """A Logging handler which extends RichHandler to write to a Widget and handle a Textual App."""

    def emit(self, record: LogRecord) -> None:
        """Invoked by logging."""
        try:
            _app = active_app.get()
        except LookupError:
            pass
        else:
            super().emit(record)


class ShowLogs(Message):
    """Custom message to show the logging messages."""

    pass


## Functions
def change_select_disabled(app, widget_id: str, disabled: bool) -> None:
    """Change the disabled state of a widget."""
    app.get_widget_by_id(widget_id).disabled = disabled
