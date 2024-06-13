from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Select

from nf_core.configs.create.utils import TextInputWithHelp

markdown_select = """
# What software environment to use?

For reproducibility purposes, Nextflow prefers to get the software used within a pipeline from a software environment or container engine.

Examples of these include `conda`, `docker`, `singularity`/`apptainer`, `charliecloud`, etc.

Here you can specify which container engine the config will use.
"""

markdown_cache = """
# Where to store software environment files and images?

By default Nextflow will download the software environment files and container images each time the pipeline is run into the run's `work/` directory.

It is highly recommended to instead specify a _cache_ directory for software environments.
This location will store files and container images downloaded by Nextflow the first time they are requested.
Subsequent runs will then re-use these files, saving time and bandwidth.
"""


class ChooseContainerType(Screen):
    """Choose which software environment source (e.g. conda or container engine) to use all configs."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_select)
        yield Center(
            Select(
                [
                    ("local (not recommended)", "conttype_local"),
                    ("conda", "conttype_conda"),
                    ("docker", "conttype_docker"),
                    ("singularity", "conttype_singularity"),
                    ("apptainer", "conttype_apptainer"),
                    ("charliecloud", "conttype_charliecloud"),
                    ("podman", "conttype_podman"),
                    ("sarus", "conttype_sarus"),
                    ("shifter", "conttype_shifter"),
                ],
                id="container_type",
            ),
            classes="cta",
        )
        yield Markdown(markdown_cache)
        yield Center(
            TextInputWithHelp(
                field_id="containercache_location",
                placeholder="",
                description="Absolute path to the container cache directory",
                markdown="",
            ),
            classes="cta",
        )

        yield Horizontal(
            Center(
                Button("Back", id="back", variant="default"),
                classes="cta",
            ),
            Center(
                Button("Next", id="containertype_continue", variant="success"),
                classes="cta",
            ),
        )
