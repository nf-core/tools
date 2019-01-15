import abc
import sys
from nf_core.workflow.parameters import Parameter

if sys.version_info >= (3, 4):
    ABC = abc.ABC
else:
    ABC = abc.ABCMeta('ABC', (), {})

class Validators(object):
    """Gives access to a factory method for objects of instance 
    :class:`Validator` which returns the correct Validator for a 
    given parameter type.
    """
    def __init__(self):
        pass
    
    @staticmethod
    def get_validator_for_param(parameter):
        """Determines matching :class:`Validator` instance for a given parameter.

        Returns:
            Validator: Matching validator for a given :class:`Parameter`.
        
        Raises:
            LookupError: In case no matching validator for a given parameter type
                can be determined.
        """
        if parameter.type == "integer":
            return IntegerValidator(parameter)
        raise LookupError("Cannot find a matching validator for type '{}'."
            .format(parameter.type))

    
class Validator(ABC):
    """Abstract base class for different parameter validators.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, parameter):
        if not isinstance(parameter, Parameter):
            raise (AttributeError("Argument must be of class {}"
                .format(Parameter.__class__)))
        self._param = parameter

    @abc.abstractmethod
    def validate(self):
        raise ValueError


class IntegerValidator(Validator):
    """Implementation for parameters of type integer.
    
    Args:
        parameter (:class:`Parameter`): A Parameter object.
    
    Raises:
        AttributeError: In case the argument is not of instance :class:`Parameter`.

    """

    def __init__(self, parameter):
        super(IntegerValidator, self).__init__(parameter)

    def validate(self):
        """Validates an parameter integer value against a given range (choices).
        If the value is valid, no error is risen.

        Raises:
            AtrributeError: Description of the value error.
        """
        value = int(self._param.value)
        choices = sorted([int(x) for x in self._param.choices])
        if not choices:
            return
        if len(choices) < 2:
            raise AttributeError("The property 'choices' must have at least two entries.")
        if not value >= choices[0] and value <= choices[-1]:
            raise AttributeError("The value for parameter '{}' must be within range of [{},{}]"
                .format(self._param.name, choices[0], choices[-1]))







