"""
Code for linting subworkflows in the nf-core/subworkflows repository and
in nf-core pipelines

Command:
nf-core subworkflows lint
"""

import logging

from nf_core.components.lint import ComponentLint, LintException, LintResult

log = logging.getLogger(__name__)


class SubworkflowLint(ComponentCommand):
    """
    An object for linting subworkflows either in a clone of the 'nf-core/modules'
    repository or in any nf-core pipeline directory
    """

    # Import lint functions
