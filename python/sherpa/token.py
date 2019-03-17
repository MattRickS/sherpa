import re

from sherpa import constants
from sherpa.exceptions import FormatError, ParseError


class Token(object):
    type = None  # type: type

    @classmethod
    def get_type(cls, string_type):
        """
        :param str  string_type:
        :rtype: cls
        """
        # Only check immediate subclasses, no tokens should subclass another
        for subcls in cls.__subclasses__():
            if subcls.type.__name__ == string_type:
                return subcls

    def __init__(self, name, default=None, choices=None, padding=None):
        """
        :param str          name:
        :param str          default:
        :param list[str]    choices:
        :param int          padding:
        """
        self._name = name
        self._default = None
        self._choices = None
        self._padding = padding or 0

        # Ensure the default value is a valid choice, and all valid values are the correct type
        if choices:
            if default and default not in choices:
                raise ValueError('Invalid default value for token {}'.format(name))
            self._choices = [self.parse(str(token)) for token in choices]

        # Convert to the token's type, raise error if an invalid type
        if default:
            self._default = self.parse(default)

    def __repr__(self):
        return "{cls}({name!r}, {default!r}, {padding!r}, {choices!r})".format(
            cls=self.__class__.__name__,
            name=self._name,
            default=self._default,
            padding=self._padding,
            choices=self._choices,
        )

    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, self._name)

    @property
    def choices(self):
        """
        :rtype: list
        """
        return self._choices[:] if self._choices else None

    @property
    def default(self):
        """
        :return: Default value for the Token or None
        """
        return self._default

    @property
    def name(self):
        """
        :rtype: str
        """
        return self._name

    @property
    def padding(self):
        """
        :rtype: int
        """
        return self._padding

    @property
    def regex(self):
        """
        :rtype: str
        """
        raise NotImplementedError

    def format(self, value):
        """
        Converts a value to a string matching this Token's format.

        :param value:
        :rtype: str
        """
        # Wildcards cannot be validated and must respect padding
        if value in (constants.WILDCARD, constants.WILDCARD_ONE):
            if self._padding:
                return constants.WILDCARD_ONE * self._padding
            return value

        try:
            value = self.type(value)
        except ValueError:
            raise FormatError('Invalid value for {self}: {value}'.format(
                self=self, value=value
            ))
        if self._choices and value not in self._choices:
            raise FormatError(
                'Invalid value for {self}: {value}. Valid values: {choices}'.format(
                    self=self, value=value, choices=self._choices
                )
            )
        string = str(value)
        return string

    def parse(self, token):
        """
        Converts a string to this Token's type

        :param str  token:
        :return:
        """
        try:
            match = re.match('^' + self.regex + '$', token)
            if match is None:
                raise ValueError
            token = self.type(token)
        except ValueError:
            raise ParseError('Invalid value for {self}: {value}'.format(
                self=self, value=token
            ))
        if self._choices and token not in self._choices:
            raise ParseError(
                'Invalid value for token {self}: {value}. Valid values: {choices}'.format(
                    self=self, value=token, choices=self._choices
                )
            )
        return token


class FloatToken(Token):
    type = float

    @property
    def regex(self):
        """
        :rtype: str
        """
        return '\d+\.\d{%s,}' % self._padding if self._padding else '\d+\.\d+'

    def format(self, value):
        """
        Converts a value to a string matching this Token's format.

        :param value:
        :rtype: str
        """
        str_value = super(FloatToken, self).format(value)
        if self._padding:
            # Add trailing 0s to meet the padding
            str_value = str_value + '0' * (self._padding - len(str_value))
        return str_value

    def parse(self, token):
        """
        Converts a string to this Token's type

        :param str  token:
        :return:
        """
        parsed = super(FloatToken, self).parse(token)
        # Float padding applies to the trailing numbers; only validate after
        # the regex has confirmed it meets the format
        if self._padding and len(token.split('.')[1]) < self._padding:
            raise ParseError(
                'Token does not match padding ({padding}) for {self}: {value!r}'.format(
                    padding=self._padding, self=self, value=token
                )
            )
        return parsed


class IntToken(Token):
    type = int

    @property
    def regex(self):
        """
        :rtype: str
        """
        return '\d{%s,}' % self._padding if self._padding else '\d+'

    def format(self, value):
        """
        Converts a value to a string matching this Token's format.

        :param value:
        :rtype: str
        """
        str_value = super(IntToken, self).format(value)
        if self._padding:
            # Add leading 0s to meet the padding
            str_value = '0' * (self._padding - len(str_value)) + str_value
        return str_value

    def parse(self, token):
        """
        Converts a string to this Token's type

        :param str  token:
        :return:
        """
        if self._padding and len(token) < self._padding:
            raise ParseError(
                'Token does not match padding ({padding}) for {self}: {value!r}'.format(
                    padding=self._padding, self=self, value=token
                )
            )
        return super(IntToken, self).parse(token)


class StringToken(Token):
    type = str
    regex = '[^/.]+'
