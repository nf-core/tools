from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, ScrollableContainer, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Switch

from nf_core.pipelines.create.utils import PipelineFeature, markdown_genomes

markdown_ci = """
Nf-core provides a set of Continuous Integration (CI) tests for Github.
When you open a pull request (PR) on your pipeline repository, these tests will run automatically.

There are different types of tests:
* Linting tests check that your code is formatted correctly and that it adheres to nf-core standards
    For code linting they will use [prettier](https://prettier.io/).
* Pipeline tests run your pipeline on a small dataset to check that it works
    These tests are run with a small test dataset on GitHub and a larger test dataset on AWS
* Marking old issues as stale
"""

markdown_badges = """
The pipeline `README.md` will include badges for:
* AWS CI Tests
* Zenodo DOI
* Nextflow
* Conda
* Docker
* Singularity
* Launching on Nextflow Tower
"""

markdown_configuration = """
Nf-core has a repository with a collection of configuration profiles.

Those config files define a set of parameters which are specific to compute environments at different Institutions.
They can be used within all nf-core pipelines.
If you are likely to be running nf-core pipelines regularly it is a good idea to use or create a custom config file for your organisation.

For more information about nf-core configuration profiles, see the [nf-core/configs repository](https://github.com/nf-core/configs)
"""


class CustomPipeline(Screen):
    """Select if the pipeline will use genomic data."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Horizontal():
            with VerticalScroll():
                yield ScrollableContainer(
                    PipelineFeature(
                        markdown_genomes,
                        "Use reference genomes",
                        "The pipeline will be configured to use a copy of the most common reference genome files from iGenomes",
                        "igenomes",
                    ),
                    PipelineFeature(
                        markdown_ci,
                        "Add Github CI tests",
                        "The pipeline will include several GitHub actions for Continuous Integration (CI) testing",
                        "ci",
                    ),
                    PipelineFeature(
                        markdown_badges,
                        "Add Github badges",
                        "The README.md file of the pipeline will include GitHub badges",
                        "github_badges",
                    ),
                    PipelineFeature(
                        markdown_configuration,
                        "Add configuration files",
                        "The pipeline will include configuration profiles containing custom parameters requried to run nf-core pipelines at different institutions",
                        "nf_core_configs",
                    ),
                )
                yield Center(
                    Button("Continue", id="continue", variant="success"),
                    classes="cta",
                )
            yield Center(self.parent.LOG_HANDLER.console, classes="cta log")

    @on(Button.Pressed, "#continue")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        skip = []
        for feature_input in self.query("PipelineFeature"):
            this_switch = feature_input.query_one(Switch)
            if not this_switch.value:
                skip.append(this_switch.id)
        self.parent.TEMPLATE_CONFIG.__dict__.update({"skip_features": skip, "is_nfcore": False})
