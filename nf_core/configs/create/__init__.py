"""A Textual app to create a config."""

import logging

import click
from rich.logging import RichHandler

## Textual objects
from textual.app import App
from textual.widgets import Button

from nf_core.configs.create import utils

## nf-core question page (screen) imports
from nf_core.configs.create.basicdetails import BasicDetails
from nf_core.configs.create.configtype import ChooseConfigType
from nf_core.configs.create.final import FinalScreen
from nf_core.configs.create.finalinfradetails import FinalInfraDetails
from nf_core.configs.create.hpccustomisation import HpcCustomisation
from nf_core.configs.create.hpcquestion import ChooseHpc
from nf_core.configs.create.nfcorequestion import ChooseNfcoreConfig
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
class ConfigsCreateApp(App[utils.ConfigsCreateConfig]):
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
        "welcome": WelcomeScreen,
        "choose_type": ChooseConfigType,
        "nfcore_question": ChooseNfcoreConfig,
        "basic_details": BasicDetails,
        "final": FinalScreen,
        "hpc_question": ChooseHpc,
        "hpc_customisation": HpcCustomisation,
        "final_infra_details": FinalInfraDetails,
    }

    # Initialise config as empty
    TEMPLATE_CONFIG = utils.ConfigsCreateConfig()

    # Tracking variables
    CONFIG_TYPE = None
    NFCORE_CONFIG = True

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
            utils.CONFIG_ISINFRASTRUCTURE_GLOBAL = True
            self.push_screen("nfcore_question")
        elif event.button.id == "type_nfcore":
            self.NFCORE_CONFIG = True
            utils.NFCORE_CONFIG_GLOBAL = True
            self.push_screen("basic_details")
        elif event.button.id == "type_pipeline":
            self.CONFIG_TYPE = "pipeline"
            utils.CONFIG_ISINFRASTRUCTURE_GLOBAL = False
            self.push_screen("nfcore_question")
        elif event.button.id == "type_custom":
            self.NFCORE_CONFIG = False
            utils.NFCORE_CONFIG_GLOBAL = False
            self.push_screen("basic_details")
        elif event.button.id == "type_hpc":
            self.push_screen("hpc_customisation")
        elif event.button.id == "toconfiguration":
            self.push_screen("final_infra_details")
        elif event.button.id == "finish":
            self.push_screen("final")
        ## General options
        if event.button.id == "close_app":
            self.exit(return_code=0)
        if event.button.id == "back":
            self.pop_screen()

    ## User theme options
    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme: str = "textual-dark" if self.theme == "textual-light" else "textual-light"
