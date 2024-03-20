from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Select

markdown_intro = """
# What job scheduler (i.e. grid executor) is running on your HPC system?

A job scheduler receives requests from all its users to run their jobs and then decides when and where to run each job on the available computing resources. It will determine where a pipeline process is run and supervise its execution. Nextflow supports many different job schedulers. See [documentation](https://www.nextflow.io/docs/latest/executor.html). 
"""

class ChooseSchedulerType(Screen):
    """Select the job scheduler running on your system."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)
        yield Center(
            Select(
                [
                    ("local (not recommended)", "scheduler_local"),
                    ("bridge", "scheduler_bridge"),
                    ("flux", "scheduler_flux"),
                    ("condor", "scheduler_htcondor"),
                    ("hyperqueue", "scheduler_hyperqueue"),
                    ("ignite", "scheduler_ignite"),
                    ("lsf", "scheduler_lsf"),
                    ("moab", "scheduler_moab"),
                    ("nsqii", "scheduler_nsqii"),
                    ("oar", "scheduler_oar"),
                    ("pbs", "scheduler_pbs"),
                    ("pbspro", "scheduler_pbspro"),
                    ("sge", "scheduler_sge"),
                    ("slurm", "scheduler_slurm"),
                ],
                id="scheduler_type",
            ),
            classes="cta",
        )
        yield Horizontal(
            Center(
                Button("Back", id="back", variant="default"),
                classes="cta",
            ),
            Center(
                Button("Next", id="schedulertype_continue", variant="success"),
                classes="cta",
            ),
        )      