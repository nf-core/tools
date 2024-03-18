"""A Textual app to create a config."""

import logging

from textual.app import App
from textual.widgets import Button

from nf_core.configs.create.basicdetails import BasicDetails
from nf_core.configs.create.custompipeline import CustomPipeline
from nf_core.configs.create.error import ExistError
from nf_core.configs.create.finaldetails import FinalDetails
from nf_core.configs.create.loggingscreen import LoggingScreen
from nf_core.configs.create.nfcoreconfigs import NfcoreConfigs
from nf_core.configs.create.pipelinetype import ChoosePipelineType
from nf_core.configs.create.utils import (
    CreateConfig,
    CustomLogHandler,
    LoggingConsole,
)
from nf_core.configs.create.welcome import WelcomeScreen

log_handler = CustomLogHandler(console=LoggingConsole(classes="log_console"), rich_tracebacks=True, markup=True)
logging.basicConfig(
    level="INFO",
    handlers=[log_handler],
    format="%(message)s",
)
log_handler.setLevel("INFO")


class ConfigsCreateApp(App[CreateConfig]):
    """A Textual app to create nf-core configs."""

    CSS_PATH = "create.tcss"
    TITLE = "nf-core configs create"
    SUB_TITLE = "Create a new nextflow config with the nf-core configs create template"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
    ]
    SCREENS = {
        "welcome": WelcomeScreen(),
        "basic_details": BasicDetails(),
    }

    # Initialise configs type
    CONFIGS_TYPE = None

    # Log handler
    LOG_HANDLER = log_handler
    # Logging state
    LOGGING_STATE = None

    def on_mount(self) -> None:
        self.push_screen("welcome")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle all button pressed events."""
        if event.button.id == "start":
            self.push_screen("choose_type")
        elif event.button.id == "type_nfcore":
            self.CONFIGS_TYPE = "infrastructure"
            self.push_screen("basic_details")
        elif event.button.id == "type_custom":
            self.CONFIGS_TYPE = "pipeline"
            self.push_screen("basic_details")
        elif event.button.id == "show_logging":
            # Set logging state to repo created to see the button for closing the logging screen
            self.LOGGING_STATE = "repo created"
            self.switch_screen(LoggingScreen())
        if event.button.id == "close_app":
            self.exit(return_code=0)
        if event.button.id == "back":
            self.pop_screen()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark: bool = not self.dark
