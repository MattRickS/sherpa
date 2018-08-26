from .exceptions import FormatError, ParseError

WILDCARD = '*'


class Token(object):
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
        return "{cls}({name!r}, default={default}, valid_values={choices})".format(
            cls=self.__class__.__name__,
            name=self._name,
            default=self._default,
            choices=self._valid_values,
        )

    def __str__(self):
        return '{}({})'.format(self._name, self.type.__name__)

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
    def type(self):
        """
        :rtype: type
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
        Converts a value to a string matching this Token's format

        :param value:
        :return:
        """
        try:
            value = self.type(value)
        except ValueError:
            raise FormatError('Invalid value for {self}: {value}'.format(
                self=self, value=value
            ))
        if self._valid_values and value != WILDCARD and value not in self._valid_values:
            raise FormatError(
                'Invalid value for {self}: {value}. Valid values: {choices}'.format(
                    self=self, value=value, choices=self._valid_values
                )
            )
        string = str(value)
        string = '0' * (self._padding - len(string)) + string
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


# As we will likely extend the Tokens, use separate classes as opposed to a
# constructor for type for ease of future development

class FloatToken(Token):
    regex = '\d+\.\d+'
    type = float


class IntToken(Token):
    regex = '\d+'
    type = int


class StringToken(Token):
    regex = '[^/]+'
    type = str


TOKEN_CLASS = {
    'str': StringToken,
    'float': FloatToken,
    'int': IntToken,
}
