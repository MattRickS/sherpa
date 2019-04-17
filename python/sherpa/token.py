import re

from sherpa import constants
from sherpa import exceptions


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
                raise exceptions.TokenConfigError(
                    'Invalid default value for token {}'.format(name)
                )
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
        if value in (constants.WILDCARD, constants.WILDCARD_ONE):
            if self._padding and self._padding[0] == self._padding[1]:
                return constants.WILDCARD_ONE * self._padding[0]
            return value

        try:
            value = self.type(value)
        except ValueError:
            raise exceptions.FormatError('Invalid value for {self}: {value}'.format(
                self=self, value=value
            ))
        if self._choices and value not in self._choices:
            raise exceptions.FormatError(
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
            raise exceptions.ParseError('Token {!r} does not match pattern: {}'.format(
                token, self.regex
            ))

        # Cast to type, particularly useful for int to float and vice versa.
        # Should never raise an exception as the regex should prevent it, but
        # kept to provide a more explicit error message if anything slips past
        try:
            token = self.type(token)
        except ValueError:
            raise exceptions.ParseError('Invalid datatype for {self}: {value}'.format(
                self=self, value=token
            ))
        if self._choices and token not in self._choices:
            raise exceptions.ParseError(
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
            parts[-1] = format_padding(self.name, decimal, self._padding)
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
            str_value = format_padding(self.name, str_value, self._padding)
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
        if string == constants.WILDCARD or all(char == constants.WILDCARD_ONE for char in string):
            return string
        # String cannot add padding
        if not fits_padding(len(string), self._padding):
            raise exceptions.FormatError(
                'Value {value!r} does not fit padding: {padding}'.format(
                    value=string, padding=self._padding
                )
            )
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
            raise exceptions.FormatError(
                'Formatted string {value!r} does not match regex: {regex}'.format(
                    value=string, regex=self.regex
                )
            )
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
        regex_padding = '+'
        if start == mid:
            pattern = '[{}]'.format(start)
        else:
            pattern = '[{}][{}]'.format(start, mid)
            # Offset by -1 as the first character is already defined
            if padding:
                lo, hi = padding
                padding = (lo - int(lo >= hi), max(hi - 1, 0))
            else:
                regex_padding = '*'

        pattern += get_padding_regex(padding) if padding else regex_padding
        return pattern


def format_padding(token_name, string, padding, char='0', left=True):
    """
    Adds additional characters to a string to fit the required padding

    :raise FormatError: if string is greater than fixed padding length

    :param str              token_name: Name of the token being padded
    :param str              string: String to pad
    :param tuple[int, int]  padding: Amount of padding expressed as (lo, hi)
    :param str              char: Additional character to add
    :param bool             left: Whether to add the padded characters to the
                                  left or right
    :rtype: str
    """
    lo, hi = padding
    count = lo - len(string)
    if count > 0:
        extra = char * count
        string = (extra + string) if left else (string + extra)
    elif count < 0 < hi:
        raise exceptions.FormatError(
            'Value {} for token {!r} is greater than fixed padding: {}'.format(
                string, token_name, hi
            )
        )
    return string


def fits_padding(size, padding):
    """
    Whether or not the given size fits in the padding range

    :param int              size:
    :param tuple[int, int]   padding:
    :rtype: bool
    """
    if padding is None:
        return True
    lo, hi = padding
    return lo <= size <= hi if hi else lo <= size


def get_padding_range(padding_string):
    """
    :raise exceptions.TokenConfigError: if given an invalid string, or padding
        is less than 0
    
    :param str  padding_string: A string indicating how much padding is required.
                         '+' indicates the value can extend in a direction, eg,
                         '3+' indicates 3 or more, while '+3' is up to 3. If no
                         '+' is given, the padding is a fixed length.
    :rtype: tuple[int, int]
    """
    # Cast to int to ensure the pattern is valid
    try:
        num = int(padding_string.strip('+'))
    except ValueError:
        raise exceptions.TokenConfigError(
            'Padding must only contain an integer and an optional "+"'
        )
    if num < 1:
        raise exceptions.TokenConfigError(
            'Padding cannot be less than 1: {}'.format(num)
        )
    if padding_string.endswith('+'):
        return num, 0
    elif padding_string.startswith('+'):
        return 1, num
    else:
        return num, num


def get_padding_regex(padding):
    """
    Gets a regex pattern matching the requested padding range

    :raise exceptions.TokenConfigError:  if there is no integer value in the
        string, or the value is less than 1

    :rtype: str
    """
    lo, hi = padding
    if 0 < hi < lo:
        raise exceptions.TokenConfigError(
            'Padding max is less than min: {},{}'.format(lo, hi)
        )
    if lo == hi == 0:
        return '*'
    lo = max(lo, 1)
    if lo == 1 and hi < 1:
        return '+'
    elif lo == hi:
        return '{%i}' % lo
    return '{%i,%s}' % (lo, max(0, hi) or '')


def get_token(token_name, config):
    """
    Creates a Token object from the token configuration

    :raise exceptions.TokenConfigError: if any token configuration values are invalid

    :param str  token_name:
    :param dict config:
    :rtype: Token
    """
    # Pop the type key so that it's not passed to Token's init
    try:
        token_type = config.pop(constants.TOKEN_TYPE)
    except KeyError:
        raise exceptions.TokenConfigError(
            'Missing token type for token: {}'.format(token_name)
        )

    cls = TOKEN_TYPES.get(token_type)
    if cls is None:
        raise exceptions.TokenConfigError('Unknown token type for {!r}: {}'.format(
            token_name, token_type
        ))

    # Convert padding to string in case it's entered as integer
    padding = config.get('padding')
    if padding is not None:
        config['padding'] = get_padding_range(str(padding))

    # Let Token validate itself, will raise any errors
    token = cls(token_name, **config)
    return token


def clashes(tokens):
    """
    Returns a dictionary mapping the indexes of all tokens in the list who clash,
    grouped by their clashing 'type' name.

    :param list[Token]|tuple[Token, ...]  tokens: List of tokens to compare
    :rtype: dict[str, tuple[Token, ...]]
    """
    # Collect tokens who use the same type
    type_mapping = {}
    for idx, token in enumerate(tokens):
        if isinstance(token, StringToken):
            # None matches both cases
            if token.case in (Case.Lower, Case.LowerCamel, None):
                type_mapping.setdefault(Case.Lower, []).append(idx)
            if token.case in (Case.Upper, Case.UpperCamel, None):
                type_mapping.setdefault(Case.Upper, []).append(idx)
            # Strings can also count as integers if numbers=True
            if token.numbers:
                type_mapping.setdefault('int', []).append(idx)
        else:
            type_mapping.setdefault(token.type.__name__, []).append(idx)

    return {k: v for k, v in type_mapping.items() if len(v) > 1}
