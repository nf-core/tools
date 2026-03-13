import subprocess
import json
import io
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Input
from textual import on

from nf_core.configs.create.utils import (
    TextInput,
    init_context,
    ConfigsCreateConfig
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
        default_queue = self._get_default_queue(scheduler)
        module_system_used = self._detect_module_system()
        yield Markdown(markdown_intro)
        with Horizontal():
            yield TextInput(
                "scheduler",
                "Scheduler",
                "The scheduler in your HPC.",
                default=scheduler if scheduler is not None else "local",
                classes="column",
            )
            yield TextInput(
                "queue",
                "Queue",
                "The default queue in your HPC.",
                default=default_queue if default_queue else "",
                classes="column",
                suggestions=queues,
            )
            yield TextInput(
                "queue_stat_interval",
                "Queue stat interval",
                "How often to get the queue status from the scheduler (minutes).",
                default="0.5",
                classes="column",
            )
        yield TextInput(
            "module_system",
            "Other modules to load",
            "Do you need to load other software using the module system for your compute nodes? Separate multiple modules by spaces.",
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
        return 'local'

    def _get_queues(self, scheduler: Optional[str]) -> list[str]:
        """Get the available queues to use for the jobs"""
        if scheduler == "slurm":
            try:
                queues = subprocess.check_output(["sinfo", "-h", "-o", '%P']).decode("utf-8")
                # Remove default * flag
                return [i.strip().replace("*", "") for i in queues.split("\n") if i]
            except subprocess.CalledProcessError:
                pass
        elif scheduler == "pbs":
            try:
                queues = json.loads(subprocess.check_output(["qstat", "-Q", "-f", "-F", "json"]).decode("utf-8"))
                return list(queues["Queue"].keys())
            except subprocess.CalledProcessError:
                pass
        elif scheduler == "sge":
            try:
                queues = subprocess.check_output(["qhost", "-q"]).decode("utf-8")
                return queues.split("\n")
            except subprocess.CalledProcessError:
                pass
        return []

    def _get_default_queue(self, scheduler: Optional[str]) -> str:
        """Get the default queue for the scheduler"""
        if scheduler == "slurm":
            try:
                return self._slurm_get_default_queue()
            except FileNotFoundError:
                pass
        elif scheduler == "pbs":
            try:
                return self._pbs_get_default_queue()
            except subprocess.CalledProcessError:
                pass
        # TODO: Implement SGE here
        return ""

    def _slurm_get_default_queue(self) -> str:
        """Get the default queue for Slurm"""
        config = {}
        # TODO: If slurm is built from source, the config file path can be different
        with open("/etc/slurm/slurm.conf", "r") as fp:
            config = self._parse_slurm_config(fp)

        for conf in config:
            if (conf["Default"] if "Default" in conf.keys() else "NO") == "YES":
                return conf["PartitionName"]
        
        # If no default is set, use the first option
        return config[0]["PartitionName"]

    def _pbs_get_default_queue(self) -> str:
        pbs_raw_config = subprocess.check_output(["qmgr", "-c", "list server"]).decode("utf-8")
        config = self._pbs_parse_config(pbs_raw_config)
        return config["default_queue"]

    def _parse_slurm_config(self, fp: Optional[io.TextIOWrapper]) -> list[dict]:
        """Parse the Slurm configuration file"""
        config = []
        for line in fp.readlines():
            if line.startswith("PartitionName"):
                tokens = [i.rsplit("=", 1) for i in line.split()]
                config.append({i[0]: i[1] for i in tokens})
        return config

    def _pbs_parse_config(self, raw: Optional[str]) -> dict:
        """Parse the PBS configuration file"""
        config = {}
        for line in [r.strip() for r in raw.split("\n")]:
            if "=" not in line:
                continue
            k, v = [token.strip() for token in line.split("=", 1)]
            config[k] = v
        return config

    def _detect_module_system(self) -> bool:
        """Detect if a module system is used"""
        try:
            subprocess.check_output(["module", "--version"])
        except FileNotFoundError:
            return False
        except subprocess.CalledProcessError:
            return False
        return True

    @on(Button.Pressed, "#toconfiguration")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        new_config = {}
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            new_config[text_input.field_id] = this_input.value
            new_config["is_infrastructure"] = True
            if not validation_result.is_valid:
                text_input.query_one(".validation_msg").update("\n".join(validation_result.failure_descriptions))
            else:
                text_input.query_one(".validation_msg").update("")
        try:
            with init_context(self.parent.get_context()):
                # First, validate the new config data
                ConfigsCreateConfig(**new_config)
                # If that passes validation, update the existing config
                self.parent.TEMPLATE_CONFIG = self.parent.TEMPLATE_CONFIG.model_copy(update=new_config)
            # Push the next screen
            self.parent.push_screen("final_infra_details")
        except ValueError:
            pass
