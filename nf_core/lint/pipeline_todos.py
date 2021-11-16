#!/usr/bin/env python

from nf_core.lint_utils import find_todos


def pipeline_todos(self):
    """Check for nf-core *TODO* lines.

    The nf-core workflow template contains a number of comment lines to help developers
    of new pipelines know where they need to edit files and add content.
    They typically have the following format:

    .. code-block:: groovy

        // TODO nf-core: Make some kind of change to the workflow here

    ..or in markdown:

    .. code-block:: html

        <!-- TODO nf-core: Add some detail to the docs here -->

    This lint test runs through all files in the pipeline and searches for these lines.
    If any are found they will throw a warning.

    .. tip:: Note that many GUI code editors have plugins to list all instances of *TODO*
              in a given project directory. This is a very quick and convenient way to get
              started on your pipeline!
    """
    results = find_todos(self)
    return results
