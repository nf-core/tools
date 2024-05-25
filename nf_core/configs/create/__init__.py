"""A Textual app to create a config."""

import logging

## Textual objects
from textual.app import App
from textual.widgets import Button

## General utilities
from nf_core.configs.create.utils import (
    CreateConfig,
    CustomLogHandler,
    LoggingConsole,
)

## nf-core question page imports
from nf_core.configs.create.welcome import WelcomeScreen

## Logging
log_handler = CustomLogHandler(
    console=LoggingConsole(classes="log_console"),
    rich_tracebacks=True,
    show_time=False,
    show_path=False,
    markup=True,
)
logging.basicConfig(
    level="INFO",
    handlers=[log_handler],
    format="%(message)s",
)
log_handler.setLevel("INFO")

## Main workflow
class ConfigsCreateApp(App[CreateConfig]):
    """A Textual app to create nf-core configs."""

    CSS_PATH = "create.tcss"
    TITLE = "nf-core configs create"
    SUB_TITLE = "Create a new nextflow config with an interactive interface"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
    ]

    ## New question screens (sections) loaded here
    SCREENS = {
        "welcome": WelcomeScreen()
    }

    # Log handler
    LOG_HANDLER = log_handler
    # Logging state
    LOGGING_STATE = None

    ## Question dialogue order defined here
    def on_mount(self) -> None:
        self.push_screen("welcome")

    ## User theme options
    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark: bool = not self.dark
