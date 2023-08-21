from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Center
from textual.widgets import Button, Footer, Header, Markdown

markdown_intro = """
# To nf-core or not to nf-core?

Next, we need to know what kind of pipeline this will be.

Choose _"nf-core"_ if:

* You want your pipeline to be part of the nf-core community
* You think that there's an outside chance that it ever _could_ be part of nf-core

Choose _"Custom"_ if:

* Your pipeline will _never_ be part of nf-core
* You want full control over *all* features that are included from the template
    (including those that are mandatory for nf-core).
"""

markdown_details = """
## Not sure? What's the difference?

Choosing _"nf-core"_ effectively pre-selects the following template features:

* GitHub Actions Continuous Integration (CI) configuration for the following:
    * Small-scale (GitHub) and large-scale (AWS) tests
    * Code format linting with prettier
    * Auto-fix functionality using @nf-core-bot
    * Marking old issues as stale
* Inclusion of shared nf-core config profiles
"""


class ChoosePipelineType(Screen):
    """Choose whether this will be an nf-core pipeline or not."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(markdown_intro)
        yield Center(
            Button("nf-core", id="type_nfcore", variant="success"),
            Button("Custom", id="type_custom", variant="primary"),
            classes="cta",
        )
        yield Markdown(markdown_details)
