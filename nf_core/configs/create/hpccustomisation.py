import subprocess
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

from nf_core.configs.create.utils import (
    TextInput,
)

markdown_intro = """
# Configure the options for your HPC
"""


class HpcCustomisation(Screen):
    """Customise the options to create a config for an HPC."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        scheduler = self._get_scheduler()
        queues = self._get_queues(scheduler)
        module_system_used = self._detect_module_system()
        yield Markdown(markdown_intro)
        with Horizontal():
            yield TextInput(
                "scheduler",
                "Scheduler",
                "The scheduler in your HPC.",
                default=scheduler if scheduler is not None else "Scheduler",
                classes="column",
            )
            yield TextInput(
                "queue",
                "Queue",
                "The queue in your HPC.",
                classes="column",
                suggestions=queues,
            )
        yield TextInput(
            "module_system",
            "Other modules to load",
            "Do you need to load other software using the module system for your compute nodes?",
            classes="hide" if not module_system_used else "",
        )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Continue", id="toconfiguration", variant="success"),
            classes="cta",
        )

    def _get_scheduler(self) -> Optional[str]:
        """Get the used scheduler"""
        try:
            subprocess.run(["sinfo", "--version"])
            return "slurm"
        except FileNotFoundError:
            pass
        except subprocess.CalledProcessError:
            pass
        try:
            subprocess.run(["qstat", "--version"])
            return "pbs"
        except FileNotFoundError:
            pass
        except subprocess.CalledProcessError:
            pass
        try:
            subprocess.run(["qstat", "-help"])
            return "sge"
        except FileNotFoundError:
            pass
        except subprocess.CalledProcessError:
            pass
        return None

    def _get_queues(self, scheduler: Optional[str]) -> list[str]:
        """Get the available queues to use for the jobs"""
        if scheduler == "slurm":
            try:
                queues = subprocess.check_output(["sinfo", "-o", '"%P,%c,%m,%l"']).decode("utf-8")
                return queues.split("\n")
            except subprocess.CalledProcessError:
                pass
        elif scheduler == "pbs":
            try:
                queues = subprocess.check_output(["qstat", "-q"]).decode("utf-8")
                return queues.split("\n")
            except subprocess.CalledProcessError:
                pass
        elif scheduler == "sge":
            try:
                queues = subprocess.check_output(["qhost", "-q"]).decode("utf-8")
                return queues.split("\n")
            except subprocess.CalledProcessError:
                pass
        return []

    def _detect_module_system(self) -> bool:
        """Detect if a module system is used"""
        try:
            subprocess.check_output(["module", "--version"])
        except FileNotFoundError:
            return False
        except subprocess.CalledProcessError:
            return False
        return True
