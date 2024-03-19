from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

from nf_core.configs.create.utils import ConfigFeature

markdown_help_text = """
Some HPC infrastructure uses module environments to load centrally installed software.
These are loaded with a command such as:

```bash
module load nextflow
````

If you need to load Nextflow and/or container engine (Singularity, Apptainer, Charliecloud etc.) via a module environment, specify this here.

If you skip this step, you must make sure all required software for running Nextflow pipelines is available in the your environment.
"""


class ChooseHpcModuleFunctionality(Screen):
    """Does your HPC infrastructure use module environments?"""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            """
# HPC specific questions
"""
        )
        yield ConfigFeature(
            markdown_help_text,
            "On",
            "Activate module environments for loading Nextflow and required dependencies (singularity, apptainer, docker, etc.)",
            "use_modules",
            False,
        )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Continue", id="envmodule_continue", variant="success"),
            classes="cta",
        )
