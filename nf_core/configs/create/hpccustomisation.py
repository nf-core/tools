import io
import json
import subprocess

from textual import on
from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown, Select

from nf_core.configs.create.utils import (
    SUPPORTED_DIRECTIVES,
    ConfigsCreateConfig,
    TextInput,
    add_hide_class,
    init_context,
    remove_hide_class,
)

markdown_intro = """
# Configure the options for your HPC

Use the following fields to provide important details about your HPC.
"""

markdown_scheduler = """
First, select your HPC's scheduler.
The program will attempt to automatically determine your HPC's scheduler.

**Please double-check that the correct scheduler was detected.**

If it was unsuccessful, you can select one of the supported schedulers from
the drop-down list.
You can also select "Local execution" which will result in jobs defaulting
to run on the same node as Nextflow; this is generally not recommended.
"""

markdown_queue = """
Next, supply your HPC's default queue, if required. Again, this will be
auto-filled if possible.
You can leave this field blank if your HPC automatically submits jobs
to a default queue when not specified.

For more complex queue selection (e.g. based on memory or CPU requirements),
you will need to manually edit the configuration file after completion.

If you wish to submit different processes to different queues, you will
need to additionally create a pipeline configuration, which will let you
specify alternative HPC queues for each process.
"""

markdown_queuestat = """
Finally, use the following field to control how frequently (in minutes) Nextflow should
request the queue status from the scheduler. This is optional, and will
default to 1 minute if not provided.
"""


class HpcCustomisation(Screen):
    """Customise the options to create a config for an HPC."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheduler = self._get_scheduler()
        self.queues = self._get_queues(self.scheduler)
        self.default_queue = self._get_default_queue(self.scheduler)
        self.supported_schedulers = {
            "Local execution": "local",
            "PBS/Torque": "pbs",
            "PBS Pro": "pbspro",
            "SGE": "sge",
            "SLURM": "slurm",
            "NQSII": "nqsii",
            "LSF": "lsf",
            "Moab": "moab",
        }
        self.supported_directives = SUPPORTED_DIRECTIVES.get(self.scheduler, ["cpus", "memory", "time", "queue"])

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        supported_schedulers = {
            "Local execution": "local",
            "PBS/Torque": "pbs",
            "PBS Pro": "pbspro",
            "SGE": "sge",
            "SLURM": "slurm",
            "NQSII": "nqsii",
            "LSF": "lsf",
            "Moab": "moab",
        }
        yield Markdown(markdown_intro)
        yield Markdown(markdown_scheduler)
        yield Select(
            list(supported_schedulers.items()),
            prompt="Select your HPC's scheduler.",
            value=self.scheduler if self.scheduler is not None else "local",
            classes="column",
            id="scheduler",
        )
        yield Markdown(markdown_queue)
        yield TextInput(
            "queue",
            "Queue name (OPTIONAL)",
            "The default queue in your HPC (leave blank if not required).",
            default=self.default_queue if self.default_queue else "",
            classes="column" if "queue" in self.supported_directives else "hide",
            suggestions=self.queues,
        )
        yield TextInput(
            "queue_stat_interval",
            "Queue stat interval (minutes) (OPTIONAL)",
            "How often (in minutes) to get the queue status from the scheduler (optional).",
            classes="column" if self.scheduler != "local" else "hide",
        )
        yield TextInput(
            "module_system",
            "Other modules to load (OPTIONAL)",
            "Do you need to load other software using the module system for your compute nodes? Separate multiple modules by spaces.",
            classes="",
        )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Continue", id="toconfiguration", variant="success"),
            classes="cta",
        )

    @on(Select.Changed, "#scheduler")
    def get_supported_directives(self, event: Select.Changed) -> None:
        """Get the supported directives for the selected scheduler."""
        self.scheduler = str(event.value)
        self.supported_directives = SUPPORTED_DIRECTIVES.get(self.scheduler, ["cpus", "memory", "time", "queue"])
        # Hide queue fields if not supported
        if "queue" in self.supported_directives:
            remove_hide_class(self.parent, "queue")
        else:
            add_hide_class(self.parent, "queue")
        if self.scheduler == "local":
            add_hide_class(self.parent, "queue_stat_interval")
        else:
            remove_hide_class(self.parent, "queue_stat_interval")

    def _get_scheduler(self) -> str | None:
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
            return "pbspro"
        except FileNotFoundError:
            pass
        except subprocess.CalledProcessError:
            pass
        try:
            subprocess.run(["qstat", "-help"])
            subprocess.run(["qhost", "-q"])
            return "sge"
        except FileNotFoundError:
            pass
        except subprocess.CalledProcessError:
            pass
        try:
            subprocess.run(["bsub", "-V"])
            return "lsf"
        except FileNotFoundError:
            pass
        except subprocess.CalledProcessError:
            pass
        try:
            subprocess.run(["moab", "--version"])
            return "moab"
        except FileNotFoundError:
            pass
        except subprocess.CalledProcessError:
            pass
        return "local"

    def _get_queues(self, scheduler: str | None) -> list[str]:
        """Get the available queues to use for the jobs"""
        if scheduler == "slurm":
            try:
                queues = subprocess.check_output(["sinfo", "-h", "-o", "%P"]).decode("utf-8")
                # Remove default * flag
                return [i.strip().replace("*", "") for i in queues.split("\n") if i]
            except subprocess.CalledProcessError:
                pass
        elif scheduler == "pbspro":
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
        # TODO: Implement LSF, Moab, NQSII here
        return []

    def _get_default_queue(self, scheduler: str | None) -> str:
        """Get the default queue for the scheduler"""
        if scheduler == "slurm":
            try:
                return self._slurm_get_default_queue()
            except FileNotFoundError:
                pass
        elif scheduler == "pbspro":
            try:
                return self._pbs_get_default_queue()
            except subprocess.CalledProcessError:
                pass
        # TODO: Implement SGE, LSF, Moab, NQSII here
        return ""

    def _slurm_get_default_queue(self) -> str:
        """Get the default queue for Slurm"""
        config = None
        # TODO: If slurm is built from source, the config file path can be different
        with open("/etc/slurm/slurm.conf") as fp:
            config = self._parse_slurm_config(fp)

        for conf in config:
            if conf.get("Default", "NO") == "YES":
                return conf["PartitionName"]

        # If no default is set, use the first option
        return config[0]["PartitionName"]

    def _pbs_get_default_queue(self) -> str:
        pbs_raw_config = subprocess.check_output(["qmgr", "-c", "list server"]).decode("utf-8")
        config = self._pbs_parse_config(pbs_raw_config)
        return config["default_queue"]

    def _parse_slurm_config(self, fp: io.TextIOWrapper) -> list[dict]:
        """Parse the Slurm configuration file"""
        config = []
        for line in fp.readlines():
            if line.startswith("PartitionName"):
                tokens = [i.rsplit("=", 1) for i in line.split()]
                config.append({i[0]: i[1] for i in tokens})
        return config

    def _pbs_parse_config(self, raw: str) -> dict:
        """Parse the PBS configuration file"""
        config = {}
        for line in [r.strip() for r in raw.split("\n")]:
            if "=" not in line:
                continue
            k, v = [token.strip() for token in line.split("=", 1)]
            config[k] = v
        return config

    @on(Button.Pressed, "#toconfiguration")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        new_config = {}

        # Get scheduler value
        select = self.query_one("#scheduler", Select)
        new_config["scheduler"] = select.value

        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            new_config[text_input.field_id] = this_input.value
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
