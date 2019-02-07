#!/usr/bin/env python

import abc
import re
import sys

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
        elif parameter.type == "string":
            return StringValidator(parameter)
        elif parameter.type == "boolean":
            return BooleanValidator(parameter)
        elif parameter.type == "decimal":
            return DecimalValidator(parameter)
        raise LookupError("Cannot find a matching validator for type '{}'."
            .format(parameter.type))


class Validator(ABC):
    """Abstract base class for different parameter validators.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, parameter):
        self._param = parameter

    @abc.abstractmethod
    def validate(self):
        raise ValueError


class IntegerValidator(Validator):
    """Implementation for parameters of type integer.

    Args:
        parameter (:class:`Parameter`): A Parameter object.

    Raises:
        AttributeError: In case the argument is not of instance integer.
    """

    def __init__(self, parameter):
        super(IntegerValidator, self).__init__(parameter)

    def validate(self):
        """Validates an parameter integer value against a given range (choices).
        If the value is valid, no error is risen.

        Raises:
            AtrributeError: Description of the value error.
        """
        value = self._param.value
        if not isinstance(value, int):
            raise AttributeError("The value {} for parameter {} needs to be an Integer, but was a {}"
                .format(value, self._param.name, type(value)))
        if self._param.choices:
            choices = sorted([x for x in self._param.choices])
            if len(choices) < 2:
                raise AttributeError("The property 'choices' must have at least two entries.")
            if not (value >= choices[0] and value <= choices[-1]):
                raise AttributeError("'{}' must be within the range [{},{}]"
                    .format(self._param.name, choices[0], choices[-1]))


class StringValidator(Validator):
    """Implementation for parameters of type string.

    Args:
        parameter (:class:`Parameter`): A Parameter object.

    Raises:
        AttributeError: In case the argument is not of instance string.
    """

    def __init__(self, parameter):
        super(StringValidator, self).__init__(parameter)

    def validate(self):
        """Validates an parameter integer value against a given range (choices).
        If the value is valid, no error is risen.

        Raises:
            AtrributeError: Description of the value error.
        """
        value = self._param.value
        if not isinstance(value, str):
            raise AttributeError("The value {} for parameter {} needs to be of type String, but was {}"
                .format(value, self._param.name, type(value)))
        choices = sorted([x for x in self._param.choices]) if self._param.choices else []
        if not choices:
            if not self._param.pattern:
                raise AttributeError("Can't validate value for parameter '{}', " \
                    "because the value for 'choices' and 'pattern' were empty.".format(self._param.value))
            result = re.match(self._param.pattern, self._param.value)
            if not result:
                raise AttributeError("'{}' doesn't match the regex pattern '{}'".format(
                        self._param.value, self._param.pattern
                    ))
        else:
            if value not in choices:
                raise AttributeError(
                    "'{}' is not not one of the choices {}".format(
                        value, str(choices)
                    )
                )


class BooleanValidator(Validator):
    """Implementation for parameters of type boolean.

    Args:
        parameter (:class:`Parameter`): A Parameter object.

    Raises:
        AttributeError: In case the argument is not of instance boolean.
    """

    def __init__(self, parameter):
        super(BooleanValidator, self).__init__(parameter)

    def validate(self):
        """Validates an parameter boolean value.
        If the value is valid, no error is risen.

        Raises:
            AtrributeError: Description of the value error.
        """
        value = self._param.value
        if not isinstance(self._param.value, bool):
            raise AttributeError("The value {} for parameter {} needs to be of type Boolean, but was {}"
                .format(value, self._param.name, type(value)))


class DecimalValidator(Validator):
    """Implementation for parameters of type boolean.

    Args:
        parameter (:class:`Parameter`): A Parameter object.

    Raises:
        AttributeError: In case the argument is not of instance decimal.
    """

    def __init__(self, parameter):
        super(DecimalValidator, self).__init__(parameter)

    def validate(self):
        """Validates an parameter boolean value.
        If the value is valid, no error is risen.

        Raises:
            AtrributeError: Description of the value error.
        """
        value = self._param.value
        if not isinstance(self._param.value, float):
            raise AttributeError("The value {} for parameter {} needs to be of type Decimal, but was {}"
                .format(value, self._param.name, type(value)))
