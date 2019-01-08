import copy
import json


class Parameters:
    """Contains a static factory method
    for :class:`Parameter` object creation.
    """
    @staticmethod
    def create_from_json(parameters_json):
        """Creates a list of Parameter objects from
        a description in JSON.

        Args:
            parameters_json (str): Parameter(s) description in JSON.

        Returns:
            list: Parameter objects.

        Raises:
            IOError, if the JSON is of unknown schema to this parser.
        """
        properties = json.loads(parameters_json)
        parameters = []
        try:
            for param in properties.get("parameters"):
                parameter = Parameter.builder().name(param.get("name")) \
                    .label(param.get("label")) \
                    .usage(param.get("usage")) \
                    .param_type(param.get("type")) \
                    .choices(param.get("choices")) \
                    .default(param.get("default_value")) \
                    .pattern(param.get("pattern")) \
                    .arity(param.get("arity")) \
                    .build()
                parameters.append(parameter)
        except Exception as e: 
            raise IOError(e)
        return parameters

    @staticmethod
    def as_json(parameters, indent=0):
        """Converts a list of Parameter objects into JSON.

        Returns:
            list: JSON formatted parameters.
        """
        params = {}
        for p in parameters:
            key = "params.{}".format(p.name)
            params[key] = str(p.value) if p.value else p.default_value
        return json.dumps(params, indent=indent)



class Parameter(object):
    """Holds information about a workflow parameter.
    """
    def __init__(self, param_builder):
        # Make some checks
        
        # Put content
        self.name = param_builder.p_name
        self.label = param_builder.p_label
        self.usage = param_builder.p_usage
        self.type = param_builder.p_type
        self.value = param_builder.p_value
        self.choices = copy.deepcopy(param_builder.p_choices)
        self.default_value = param_builder.p_default_value
        self.pattern = param_builder.p_pattern
        self.arity = param_builder.p_arity
    
    @staticmethod
    def builder():
        return ParameterBuilder()

class ParameterBuilder:
    """Parameter builder.
    """
    def __init__(self):
        self.p_name = ""
        self.p_label = ""
        self.p_usage = ""
        self.p_type = ""
        self.p_value = ""
        self.p_choices = []
        self.p_default_value = ""
        self.p_pattern = ""
        self.p_arity = ""
    
    def name(self, name):
        """Sets the parameter name.

        Args:
            name (str): Parameter name.
        """
        self.p_name = name
        return self
    
    def label(self, label):
        """Sets the parameter label.

        Args:
            label (str): Parameter label.
        """
        self.p_label = label
        return self
    
    def usage(self, usage):
        """Sets the parameter usage.

        Args:
            usage (str): Parameter usage description.
        """
        self.p_usage = usage
        return self
    
    def value(self, value):
        """Sets the parameter value.

        Args:
            value (str): Parameter value.
        """
        self.p_value = value
        return self
    
    def choices(self, choices):
        """Sets the parameter value choices.

        Args:
            choices (list): Parameter value choices.
        """
        self.p_choices = choices
        return self
    
    def param_type(self, param_type):
        """Sets the parameter type.

        Args:
            param_type (str): Parameter type.
        """
        self.p_type = param_type
        return self
    
    def default(self, default):
        """Sets the parameter default value.

        Args:
            default (str): Parameter default value.
        """
        self.p_default_value = default
        return self
    
    def pattern(self, pattern):
        """Sets the parameter regex pattern.

        Args:
            pattern (str): Parameter regex pattern.
        """
        self.p_pattern = pattern
        return self
    
    def arity(self, arity):
        """Sets the parameter regex pattern.

        Args:
            pattern (str): Parameter regex pattern.
        """
        self.p_arity = arity
        return self
    
    def build(self):
        """Builds parameter object.

        Returns:
            Parameter: Fresh from the factory.
        """
        return Parameter(self)

