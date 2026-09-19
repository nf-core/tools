import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Rendered as the two canonical pages
CANONICAL_PAGES = ["usage.md", "output.md"]
# Markdown under these is rendered as sub-pages of the corresponding section
SECTION_DIRS = ["usage", "output"]
# Documentation about the repo rather than pages for the website
NOT_PAGES = ["README.md", "CONTRIBUTING.md"]
# Skipped by the website itself
SKIPPED_DIRS = ["images"]


def docs_pages(self):
    """Check that every documentation page will be rendered on the nf-core website.

    The website generates a page for a markdown file in ``docs/`` only if it is
    ``docs/usage.md`` or ``docs/output.md``, or lives under ``docs/usage/`` or
    ``docs/output/``. A page placed anywhere else in ``docs/`` displays correctly on
    GitHub but returns a 404 on the website, with nothing to indicate that it is missing.

    To publish an additional page, put it in one of the two section directories, e.g.
    ``docs/usage/troubleshooting.md``, which is rendered at
    ``/<pipeline>/<version>/docs/usage/troubleshooting/``.

    ``docs/README.md``, ``docs/CONTRIBUTING.md`` and anything under ``docs/images/``
    describe the repository rather than the pipeline, and are not checked.

    .. note:: You can choose to ignore this lint test by editing the file called
        ``.nf-core.yml`` in the root of your pipeline and setting the test to false:

        .. code-block:: yaml

            lint:
                docs_pages: False

        To keep a working document in ``docs/`` without publishing it, list it instead:

        .. code-block:: yaml

            lint:
                docs_pages:
                    - docs/implementation_design.md

    """
    passed = []
    warned = []
    ignored = []

    ignored_config = self.lint_config.get("docs_pages", []) if self.lint_config is not None else []

    docs_dir = Path(self.wf_path, "docs")
    if not docs_dir.is_dir():
        return {"passed": passed, "warned": warned, "ignored": ignored}

    for fname in sorted(docs_dir.glob("**/*.md*")):
        if fname.suffix not in [".md", ".mdx"]:
            continue
        rel_path = fname.relative_to(self.wf_path)
        parts = rel_path.parts[1:]

        if parts[0] in SKIPPED_DIRS or parts[-1] in NOT_PAGES:
            continue

        if str(rel_path) in ignored_config:
            ignored.append(f"Ignoring documentation page `{rel_path}`")
            continue

        if (len(parts) == 1 and parts[0] in CANONICAL_PAGES) or parts[0] in SECTION_DIRS:
            passed.append(f"Documentation page will be rendered on the website: `{rel_path}`")
        else:
            warned.append(
                f"Documentation page will not be rendered on the website: `{rel_path}`. "
                f"Move it to `docs/{SECTION_DIRS[0]}/{parts[-1]}` to publish it as a sub-page of the "
                f"{SECTION_DIRS[0]} section."
            )

    return {"passed": passed, "warned": warned, "ignored": ignored}
