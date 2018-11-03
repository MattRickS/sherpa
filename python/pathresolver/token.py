from pathresolver import constants
from pathresolver.exceptions import FormatError, ParseError


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

    def __init__(self, name, default=None, padding=None, valid_values=None):
        """
        :param str  name:
        :param str  default:
        :param int  padding:
        :param list valid_values:
        """
        self._name = name
        self._default = None
        self._padding = padding or 0
        self._valid_values = None

        # Ensure the default value is a valid choice, and all valid values are the correct type
        if valid_values:
            if default and default not in valid_values:
                raise ValueError('Invalid default value for token {}'.format(name))
            self._valid_values = [self.parse(token) for token in valid_values]

        # Convert to the token's type, raise error if an invalid type
        if default:
            self._default = self.parse(default)

    def __repr__(self):
        return "{cls}({name!r}, {default!r}, {padding!r}, {choices!r})".format(
            cls=self.__class__.__name__,
            name=self._name,
            default=self._default,
            padding=self._padding,
            choices=self._valid_values,
        )

    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, self._name)

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

    @property
    def valid_values(self):
        """
        :rtype: list
        """
        return self._valid_values[:] if self._valid_values else None

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
        if self._valid_values and value not in self._valid_values:
            raise FormatError(
                'Invalid value for {self}: {value}. Valid values: {choices}'.format(
                    self=self, value=value, choices=self._valid_values
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
        if len(token) < self._padding:
            raise ParseError(
                'Token length does not match padding ({padding}) for {self}: {value}'.format(
                    padding=self._padding, self=self, value=token
                )
            )
        try:
            token = self.type(token)
        except ValueError:
            raise ParseError('Invalid value for {self}: {value}'.format(
                self=self, value=token
            ))
        if self._valid_values and token not in self._valid_values:
            raise ParseError(
                'Invalid value for token {self}: {value}. Valid values: {choices}'.format(
                    self=self, value=token, choices=self._valid_values
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


class StringToken(Token):
    type = str

    @property
    def regex(self):
        """
        :rtype: str
        """
        return '[^/]{%s,}' % self._padding if self._padding else '[^/]+'
