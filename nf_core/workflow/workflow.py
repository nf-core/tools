#!/usr/bin/env python

from nf_core.workflow.parameters import Parameters


class Workflow(object):
    """nf-core workflow object that holds run parameter information.

    Args:
        name (str): Workflow name.
        parameters_json (str): Workflow parameter data in JSON.
    """
    def __init__(self, name, parameters_json):
        self.name = name
        self.parameters = Parameters.create_from_json(parameters_json)

    def in_nextflow_json(self, indent=0):
        """Converts the Parameter list in a workflow readable parameter
        JSON file.

        Returns:
            str: JSON formatted parameters.
        """
        return Parameters.in_nextflow_json(self.parameters, indent)

    def in_full_json(self, indent=0):
        """Converts the Parameter list in a complete parameter JSON for
        schema validation.

        Returns:
            str: JSON formatted parameters.
        """
        return Parameters.in_full_json(self.parameters, indent)
