#!/usr/bin/env python
import logging
from nf_core.lint.pipeline_todos import pipeline_todos

log = logging.getLogger(__name__)


def module_todos(module_lint_object, module):
    """
    Look for TODO statements in the module files

    The nf-core module template contains a number of comment lines to help developers
    of new modules know where they need to edit files and add content.
    They typically have the following format:

    .. code-block:: groovy

        // TODO nf-core: Make some kind of change to the workflow here

    ..or in markdown:

    .. code-block:: html

        <!-- TODO nf-core: Add some detail to the docs here -->

    This lint test runs through all files in the module and searches for these lines.
    If any are found they will throw a warning.

    .. tip:: Note that many GUI code editors have plugins to list all instances of *TODO*
              in a given project directory. This is a very quick and convenient way to get
              started on your pipeline!

    """
    module.wf_path = module.module_dir
    results = pipeline_todos(module)
    for i, warning in enumerate(results["warned"]):
        module.warned.append(("module_todo", warning, results["file_paths"][i]))
