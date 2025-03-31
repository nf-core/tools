"""A Textual app to create a config."""

import logging

import click
from rich.logging import RichHandler

## Textual objects
from textual.app import App
from textual.widgets import Button

## nf-core question page (screen) imports
from nf_core.configs.create.basicdetails import BasicDetails
from nf_core.configs.create.configtype import ChooseConfigType
from nf_core.configs.create.final import FinalScreen
from nf_core.configs.create.utils import CreateConfig
from nf_core.configs.create.welcome import WelcomeScreen

## General utilities
from nf_core.utils import LoggingConsole

## Logging
logger = logging.getLogger(__name__)
rich_log_handler = RichHandler(
    console=LoggingConsole(classes="log_console"),
    level=logging.INFO,
    rich_tracebacks=True,
    show_time=False,
    show_path=False,
    markup=True,
    tracebacks_suppress=[click],
)
logger.addHandler(rich_log_handler)


## Main workflow
class ConfigsCreateApp(App[CreateConfig]):
    """A Textual app to create nf-core configs."""

    CSS_PATH = "../../textual.tcss"
    TITLE = "nf-core configs create"
    SUB_TITLE = "Create a new nextflow config with an interactive interface"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
    ]

    ## New question screens (sections) loaded here
    SCREENS = {
        "welcome": WelcomeScreen(),
        "choose_type": ChooseConfigType(),
        "basic_details": BasicDetails(),
        "final": FinalScreen(),
    }

    # Initialise config as empty
    TEMPLATE_CONFIG = CreateConfig()

    # Tracking variables
    CONFIG_TYPE = None

    # Log handler
    LOG_HANDLER = rich_log_handler
    # Logging state
    LOGGING_STATE = None

    ## Question dialogue order defined here
    def on_mount(self) -> None:
        self.push_screen("welcome")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle all button pressed events."""
        if event.button.id == "lets_go":
            self.push_screen("choose_type")
        elif event.button.id == "type_infrastructure":
            self.CONFIG_TYPE = "infrastructure"
            self.push_screen("basic_details")
        elif event.button.id == "type_pipeline":
            self.CONFIG_TYPE = "pipeline"
            self.push_screen("basic_details")
        elif event.button.id == "next":
            self.push_screen("final")
        ## General options
        if event.button.id == "close_app":
            self.exit(return_code=0)
        if event.button.id == "back":
            self.pop_screen()

    ## User theme options
    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark: bool = not self.dark
