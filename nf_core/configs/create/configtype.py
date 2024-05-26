from textual.app import ComposeResult
from textual.containers import Center, Grid
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

markdown_intro = """
# Choose config type
"""

markdown_type_nfcore = """
## Choose _"Infrastructure config"_ if:

* You want to only define the computational environment you will run all pipelines on


"""
markdown_type_custom = """
## Choose _"Pipeline config"_ if:

* You just want to tweak resources of a particular step of a specific pipeline.
"""

markdown_details = """
## What's the difference?

_Infrastructure_ configs:

- Describe the basic necessary information for any nf-core pipeline to
execute
- Define things such as which container engine to use, if there is a scheduler and
which queues to use etc.
- Are suitable for _all_ users on a given computing environment.
- Can be uploaded to [nf-core
configs](https://github.com/nf-core/tools/configs) to be directly accessible
in a nf-core pipeline with `-profile <infrastructure_name>`.
- Are not used to tweak specific parts of a given pipeline (such as a process or
module)

_Pipeline_ configs

- Are config files that target specific component of a particular pipeline or pipeline run.
    - Example: you have a particular step of the pipeline that often runs out
of memory using the pipeline's default settings. You would use this config to
increase the amount of memory Nextflow supplies that given task.
- Are normally only used by a _single or small group_ of users.
- _May_ also be shared amongst multiple users on the same
computing environment if running similar data with the same pipeline.
- Can _sometimes_ be uploaded to [nf-core
configs](https://github.com/nf-core/tools/configs) as a 'pipeline-specific'
config.


"""


class ChooseConfigType(Screen):
    """Choose whether this will be an infrastructure or pipeline config."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)
        yield Grid(
            Center(
                Markdown(markdown_type_nfcore),
                Center(Button("Pipeline config", id="type_infrastructure", variant="success")),
            ),
            Center(
                Markdown(markdown_type_custom),
                Center(Button("Infrastructure config", id="type_pipeline", variant="primary")),
            ),
            classes="col-2 pipeline-type-grid",
        )
        yield Markdown(markdown_details)
