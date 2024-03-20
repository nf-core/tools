"""A Textual app to create a pipeline."""

from textwrap import dedent

from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

from nf_core.configs.create.utils import TextInputWithHelp


class MaxparamsOptions(Screen):
    """Name, description, author, etc."""

    def compose(self) -> ComposeResult:
        default_cpus = 8
        default_memory = 32
        default_time = 24

        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Specify maximum resource parameters

                These values are used to set the absolute maximum resources that CAN be requested by a pipeline.

                They do not _increase_ resources requests (for this, create a `pipeline` config), but rather act as a cap.
                """
            )
        )
        yield TextInputWithHelp(
            "max_cpus",
            str(default_cpus),
            "Maximum CPUs",
            "Define the maximum number of CPUs that the computing infrastructure has. This is the maximum number of CPUs of a laptop or desktop, the number of CPUs on the largest node on a HPC cluster.",
            default=str(default_cpus),
            classes="row",
        )
        yield TextInputWithHelp(
            "max_mem",
            str(default_memory),
            "Maximum memory (GB)",
            "Define the maximum number of memory (RAM) that the computing infrastructure has. This is the RAM of a laptop or desktop, or the RAM on the largest node on a HPC cluster.",
            default=str(default_memory),
            classes="row",
        )
        yield TextInputWithHelp(
            "max_time",
            str(default_time),
            "Maximum wall time (hours)",
            "Define the maximum length a step of a pipeline can run for. Set to something sensible for a laptop or desktop, set to value of the partition with the longest walltime on a HPC cluster.",
            default=str(default_time),
            classes="custom_grid",
        )

        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Next", id="maxparams_continue", variant="success"),
            classes="cta",
        )
