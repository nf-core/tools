#!/usr/bin/env python
"""
The SubworkflowsTest class runs the tests locally
"""

from nf_core.components.components_test import ComponentsTest


class SubworkflowsTest(ComponentsTest):
    """
    Class to run module pytests.
    """

    def __init__(
        self,
        component_name=None,
        no_prompts=False,
        pytest_args="",
        remote_url=None,
        branch=None,
        no_pull=False,
    ):
        super().__init__(
            component_type="subworkflows",
            module_name=component_name,
            no_prompts=no_prompts,
            pytest_args=pytest_args,
            remote_url=remote_url,
            branch=branch,
            no_pull=no_pull,
        )
