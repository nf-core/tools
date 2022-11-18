"""
The ModulesTest class runs the tests locally
"""

from nf_core.components.components_test import ComponentsTest


class ModulesTest(ComponentsTest):
    """
    Class to run module pytests.
    """

    def __init__(
        self,
        module_name=None,
        no_prompts=False,
        pytest_args="",
        remote_url=None,
        branch=None,
        no_pull=False,
    ):
        super().__init__(
            component_type="modules",
            component_name=module_name,
            no_prompts=no_prompts,
            pytest_args=pytest_args,
            remote_url=remote_url,
            branch=branch,
            no_pull=no_pull,
        )
