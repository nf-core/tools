from textual.app import ComposeResult
from textual.containers import Center, HorizontalScroll, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static, Switch

markdown_genomes = """
Nf-core pipelines are configured to use a copy of the most common reference genome files.

By selecting this option, your pipeline will include a configuration file specifying the paths to these files.

The required code to use these files will also be included in the template.
When the pipeline user provides an appropriate genome key,
the pipeline will automatically download the required reference files.

For more information about reference genomes in nf-core pipelines,
see the [nf-core docs](https://nf-co.re/docs/usage/reference_genomes).
"""

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


class HelpText(Markdown):
    """A class to show a text box with help text."""

    def __init__(self, markdown: str, classes: str) -> None:
        super().__init__(markdown=markdown, classes=classes)

    def show(self) -> None:
        """Method to show the help text box."""
        self.add_class("displayed")

    def hide(self) -> None:
        """Method to hide the help text box."""
        self.remove_class("displayed")


class PipelineFeature(Static):
    """Widget for the selection of pipeline features."""

    def __init__(self, markdown: str, title: str, subtitle: str) -> None:
        self.markdown = markdown
        self.title = title
        self.subtitle = subtitle
        super().__init__()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """When the button is pressed, change the type of the button."""
        if event.button.id == "show_help":
            self.add_class("displayed")
        elif event.button.id == "hide_help":
            self.remove_class("displayed")

    def compose(self) -> ComposeResult:
        """
        Create child widgets.

        Displayed row with a switch, a short text description and a help button.
        Hidden row with a help text box.
        """
        yield HorizontalScroll(
            Switch(value=True),
            Static(self.title, classes="feature_title"),
            Static(self.subtitle, classes="feature_subtitle"),
            Button("Show help", id="show_help", variant="primary"),
            Button("Hide help", id="hide_help"),
            classes="custom_grid",
        )
        yield HelpText(self.markdown, classes="help_box")


class CustomPipeline(Screen):
    """Select if the pipeline will use genomic data."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield ScrollableContainer(
            PipelineFeature(
                markdown_genomes,
                "Use reference genomes",
                "The pipeline will be configured to use a copy of the most common reference genome files from iGenomes",
            ),
            PipelineFeature(
                markdown_ci,
                "Add Github CI tests",
                "The pipeline will include several GitHub actions for Continuous Integration (CI) testing",
            ),
            PipelineFeature(
                markdown_badges,
                "Add Github badges",
                "The README.md file of the pipeline will include GitHub badges",
            ),
            PipelineFeature(
                markdown_configuration,
                "Add configuration files",
                "The pipeline will include configuration profiles containing custom parameters requried to run nf-core pipelines at different institutions",
            ),
        )
        yield Center(
            Button("Done", id="custom_done", variant="success"),
            classes="cta",
        )
