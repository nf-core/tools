import abc
from nf_core.workflow.parameters import Parameter

class Validators(object):
    """
    """
    def __init__(self):
        pass
    
    @staticmethod
    def get_validator_for_param(parameter):
        """Returns a validator object for a given parameter.
        """
        if parameter.type == "integer":
            return IntegerValidator(parameter)
        raise LookupError("Cannot find a matching validator for type '{}'."
            .format(parameter.type))

    
class Validator(abc.ABC):
    """Abstract base class for different parameter validators.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, parameter):
        if not isinstance(parameter, Parameter):
            raise (AttributeError("Argument must be of class {}"
                .format(parameters.Parameter.__class__.__module__)))
        self._param = parameter

    @abc.abstractmethod
    def validate(self):
        raise ValueError


class IntegerValidator(Validator):
    """Implementation for parameters of type integer."""

    def __init__(self, params):
        super(IntegerValidator, self).__init__(params)

    def validate(self):
        value = int(self._param.value)
        choices = sorted([int(x) for x in self._param.choices])
        if not choices:
            return
        if len(choices) < 2:
            raise AttributeError("The property 'choices' must have at least two entries.")
        if not value >= choices[0] and value <= choices[-1]:
            raise AttributeError("The value for parameter '{}' must be within range of [{},{}]"
                .format(self.__param.name, choices[0], choices[-1]))







