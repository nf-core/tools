from nf_core.parameters import Parameters
from nf_core.parameters import Parameter

class Workflow(object):
    """nf-core workflow object that holds run parameter information.

    Args:
        name (str): Workflow name.
        parameters_json (str): Workflow parameter data in JSON. 
    """
    def __init__(self, name, parameters_json):
        self.name = name
        self.parameters = Parameters.create_from_json(parameters_json)
    
    def as_params_json(self, indent=0):
        """Converts the Parameter list in a workflow readable parameter
        JSON file.

        Returns:
            str: JSON formatted parameters.
        """
        return Parameters.as_json(self.parameters, indent)

