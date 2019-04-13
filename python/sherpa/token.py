import re

from sherpa import constants
from sherpa.exceptions import FormatError, ParseError


class Token(object):
    type = None  # type: type

    def __init__(self, name, default=None, choices=None, padding=None):
        """
        :param str              name:
        :param str              default:
        :param list[str]        choices:
        :param tuple[int, int]  padding:
        """
        self._name = name
        self._default = None
        self._choices = None
        self._padding = padding

        # Ensure the default value is a valid choice, and all valid values are the correct type
        if choices:
            if default and default not in choices:
                raise ValueError('Invalid default value for token {}'.format(name))
            # Note: choices must be declared above as parse() requires it
            self._choices = [self.parse(str(token)) for token in choices]

        # Convert to the token's type, raise error if an invalid type
        if default:
            self._default = self.parse(default)

    def __repr__(self):
        return ("{self.__class__.__name__}({self._name!r}, default={self._default!r}, "
                "choices={self._choices!r}, padding={self._padding!r})".format(self=self))

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
        :rtype: tuple[int, int]
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
        # Wildcards cannot be validated and must respect padding. Padding ranges
        # can't use an explicit number of wildcards
        # TODO: Parse strings after searching with formatted wilcards on padded ranges
        if value in (constants.WILDCARD, constants.WILDCARD_ONE):
            if self._padding and self._padding[0] == self._padding[1]:
                return constants.WILDCARD_ONE * self._padding[0]
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
        match = re.match('^' + self.regex + '$', token)
        if match is None:
            raise ParseError('Token {!r} does not match pattern: {}'.format(token, self.regex))
        try:
            token = self.type(token)
        except ValueError:
            raise ParseError('Invalid datatype for {self}: {value}'.format(
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
        pattern = '\d+\.\d'
        pattern += get_padding_regex(self._padding) if self._padding else '+'
        return pattern

    def format(self, value):
        """
        Converts a value to a string matching this Token's format.

        :param value:
        :rtype: str
        """
        str_value = super(FloatToken, self).format(value)
        if self._padding:
            # Add trailing 0s to meet the padding
            parts = str_value.split('.')
            decimal = parts[-1]
            parts[-1] = format_padding(decimal, self._padding)
            str_value = '.'.join(parts)
        return str_value


class IntToken(Token):
    type = int

    @property
    def regex(self):
        """
        :rtype: str
        """
        pattern = '\d'
        pattern += get_padding_regex(self._padding) if self._padding else '+'
        return pattern

    def format(self, value):
        """
        Converts a value to a string matching this Token's format.

        :param value:
        :rtype: str
        """
        str_value = super(IntToken, self).format(value)
        if self._padding:
            str_value = format_padding(str_value, self._padding)
        return str_value


class StringToken(Token):
    type = str

    def __init__(self, name, default=None, choices=None, padding=None, case=None, numbers=True):
        self._case = case.lower() if case else None
        self._numbers = numbers
        if self._case is not None:
            regex = Case.get_regex(self._case, numbers=numbers, padding=padding)
        else:
            if self._numbers:
                regex = '[^{}]'.format(constants.STRING_BLACKLIST)
            else:
                regex = '[^{}{}]'.format(constants.STRING_BLACKLIST, constants.NUMBER_PATTERN)
            regex += get_padding_regex(padding) if padding else '+'
        self._regex = regex
        # Initialise regex before calling super as the init parses the default/choices
        super(StringToken, self).__init__(name, default=default, choices=choices, padding=padding)

    @property
    def case(self):
        # type: () -> str
        return self._case

    @property
    def numbers(self):
        # type: () -> bool
        return self._numbers

    @property
    def regex(self):
        # type: () -> str
        return self._regex

    def format(self, value):
        string = super(StringToken, self).format(value)
        # String cannot add padding
        if not fits_padding(len(string), self._padding):
            raise FormatError('Value {value!r} does not fit padding: {padding}'.format(
                value=string, padding=self._padding
            ))
        if self._case == Case.Upper:
            string = string.upper()
        elif self._case == Case.Lower:
            string = string.lower()
        elif self._case == Case.LowerCamel:
            string = string[0].lower() + string[1:]
        elif self._case == Case.UpperCamel:
            string = string[0].upper() + string[1:]
        # Catch any blacklisted characters, ensure we match the whole string
        if not re.match('^' + self.regex + '$', string):
            raise FormatError('Formatted string {value!r} does not match regex: {regex}'.format(
                value=string, regex=self.regex
            ))
        return string


class SequenceToken(IntToken):
    """
    Can be formatted with common padding string values, eg, #### or %04d, but
    otherwise is treated as an IntToken.
    """

    def __init__(self, name, default=None, choices=None, padding=None):
        super(SequenceToken, self).__init__(name, default=default, choices=choices, padding=padding)

    @property
    def regex(self):
        padding = get_padding_regex(self._padding) if self._padding else '+'
        return '[\d#]{}|%{}d'.format(padding, '%02d' % self._padding[0] if self._padding else '\d+')

    def format(self, value):
        return value if self.is_sequence_pattern(str(value)) else super(SequenceToken, self).format(value)

    def parse(self, token):
        return token if self.is_sequence_pattern(token) else super(SequenceToken, self).parse(token)

    def is_sequence_pattern(self, value):
        if all(char == '#' for char in value) and fits_padding(len(value), self._padding):
            return True
        match = re.match('%(\d+)d', value)
        if match:
            return fits_padding(int(match.group(1)), self._padding)
        return False


TOKEN_TYPES = {
    'int': IntToken,
    'float': FloatToken,
    'str': StringToken,
    'sequence': SequenceToken,
}


class Case(object):
    LowerCamel = 'lowercamel'
    UpperCamel = 'uppercamel'
    Lower = 'lower'
    Upper = 'upper'

    _PATTERNS = {
        LowerCamel: ('a-z', 'a-zA-Z'),
        UpperCamel: ('A-Z', 'a-zA-Z'),
        Lower: ('a-z', 'a-z'),
        Upper: ('A-Z', 'A-Z'),
    }

    @classmethod
    def get_regex(cls, case, numbers=False, padding=None):
        """
        :param str  case: Case to build pattern for
        :param bool numbers: Whether or not numbers are allowed in the string.
                             Does not affect the first character.
        :param tuple[int, int] padding: Tuple for (lo, hi) padding range
        :rtype: str
        """
        start, mid = cls._PATTERNS[case.lower()]
        if numbers:
            mid += constants.NUMBER_PATTERN

        # For tidiness sake, compress identical patterns
        if start == mid:
            pattern = '[{}]'.format(start)
        else:
            pattern = '[{}][{}]'.format(start, mid)
            # Offset by -1 as the first character is already defined
            if padding:
                lo, hi = padding
                padding = (lo - int(lo == hi), max(hi - 1, 0))

        pattern += get_padding_regex(padding) if padding else '*'
        return pattern


def format_padding(string, padding, char='0', left=True):
    num = min(i for i in padding if i)
    extra = char * (num - len(string))
    if extra:
        string = (extra + string) if left else (string + extra)
    return string


def fits_padding(size, padding):
    if padding is None:
        return True
    lo, hi = padding
    return lo <= size <= hi if hi else lo <= size


def get_padding_range(padding):
    """


    :param str  padding: A string indicating how much padding is required.
                         '+' indicates the value can extend in a direction, eg,
                         '3+' indicates 3 or more, while '+3' is up to 3. If no
                         '+' is given, the padding is a fixed length.
    :rtype: tuple[int, int]
    """
    # Cast to int to ensure the pattern is valid
    num = int(padding.strip('+'))
    if num < 1:
        raise ValueError('Padding cannot be less than 1: {}'.format(num))
    if padding.endswith('+'):
        return num, 0
    elif padding.startswith('+'):
        return 1, num
    else:
        return num, num


def get_padding_regex(padding):
    """
    Gets a regex pattern matching the requested padding range

    :raise ValueError:  if there is no integer value in the string, or the value
                        is less than 1

    :rtype: str
    """
    lo, hi = padding
    if 0 < hi < lo:
        raise ValueError('Padding max is less than min: {},{}'.format(lo, hi))
    if lo == hi == 0:
        return '*'
    lo = max(lo, 1)
    if lo == 1 and hi < 1:
        return '+'
    elif lo == hi:
        return '{%i}' % lo
    return '{%i,%s}' % (lo, max(0, hi) or '')


def get_token(token_name, config):
    # Pop the type key so that it's not passed to Token's init
    try:
        token_type = config.pop(constants.TOKEN_TYPE)
    except KeyError:
        raise KeyError('Missing token type for token: {}'.format(token_name))

    cls = TOKEN_TYPES.get(token_type)
    if cls is None:
        raise KeyError('Unknown token type for {!r}: {}'.format(
            token_name, token_type
        ))

    # Convert padding to string in case it's entered as integer
    padding = config.get('padding')
    if padding is not None:
        config['padding'] = get_padding_range(str(padding))

    # Let Token validate itself, will raise any errors
    token = cls(token_name, **config)
    return token


if __name__ == '__main__':
    for case in (Case.Lower, Case.Upper, Case.LowerCamel, Case.UpperCamel):
        for numbers in (True, False):
            for padding in (None, (3, 0), (1, 3), (3, 3)):
                print('-' * 20)
                print(case, numbers, padding)
                token = StringToken('one', case=case, padding=padding, numbers=numbers)
                print(token.regex)
                for val in ('oneTwo', 'three', 'one1', 'THREE'):
                    try:
                        print('Parsed:', token.parse(val))
                    except ParseError:
                        print('Cannot parse: {!r}'.format(val))
