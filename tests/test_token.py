import pytest

from sherpa import constants
from sherpa import token
from sherpa.exceptions import ParseError, FormatError


@pytest.mark.parametrize('string_type, cls', (
    ('float', token.FloatToken),
    ('int', token.IntToken),
    ('str', token.StringToken),
))
def test_get_token(string_type, cls):
    assert token.get_token('name', {constants.TOKEN_TYPE: string_type}).__class__ == cls


@pytest.mark.parametrize('fields, exception', (
    ({'case': token.Case.Lower}, KeyError),    # no token type
    ({constants.TOKEN_TYPE: None}, KeyError),  # Unknown token type
    ({constants.TOKEN_TYPE: 'str',
      'default': 'abc',
      'choices': ['a', 'b']}, ValueError),      # Default not in choices
))
def test_get_token_fail(fields, exception):
    with pytest.raises(exception):
        assert token.get_token('name', fields)


@pytest.mark.parametrize('string, expected', (
    ('3', (3, 3)),
    ('3+', (3, 0)),
    ('+3', (1, 3)),
))
def test_get_padding_range(string, expected):
    assert token.get_padding_range(string) == expected


@pytest.mark.parametrize('string', ('8a', '+0', '0', '0+'))
def test_get_padding_range_fail(string):
    with pytest.raises(ValueError):
        token.get_padding_range(string)


@pytest.mark.parametrize('padding, expected', (
    ((3, 3), '{3}'),
    ((3, 0), '{3,}'),
    ((1, 5), '{1,5}'),
    ((1, 0), '+'),
    ((0, 0), '*'),
))
def test_get_padding_regex(padding, expected):
    assert token.get_padding_regex(padding) == expected


def test_get_padding_regex_fail():
    with pytest.raises(ValueError):
        token.get_padding_regex((3, 1))


@pytest.mark.parametrize('kwargs, expected', (
    ({'case': token.Case.Lower}, '[a-z]+'),
    ({'case': token.Case.Upper}, '[A-Z]+'),
    ({'case': token.Case.LowerCamel}, '[a-z][a-zA-Z]*'),
    ({'case': token.Case.UpperCamel}, '[A-Z][a-zA-Z]*'),

    ({'case': token.Case.Lower, 'numbers': True}, '[a-z][a-z0-9]*'),
    ({'case': token.Case.Upper, 'numbers': True}, '[A-Z][A-Z0-9]*'),
    ({'case': token.Case.LowerCamel, 'numbers': True}, '[a-z][a-zA-Z0-9]*'),
    ({'case': token.Case.UpperCamel, 'numbers': True}, '[A-Z][a-zA-Z0-9]*'),

    ({'case': token.Case.Lower, 'numbers': True, 'padding': (3, 3)}, '[a-z][a-z0-9]{2}'),
    ({'case': token.Case.Upper, 'numbers': True, 'padding': (3, 3)}, '[A-Z][A-Z0-9]{2}'),
    ({'case': token.Case.LowerCamel, 'numbers': True, 'padding': (3, 3)}, '[a-z][a-zA-Z0-9]{2}'),
    ({'case': token.Case.UpperCamel, 'numbers': True, 'padding': (3, 3)}, '[A-Z][a-zA-Z0-9]{2}'),

    ({'case': token.Case.Lower, 'padding': (3, 3)}, '[a-z]{3}'),
    ({'case': token.Case.Upper, 'padding': (3, 3)}, '[A-Z]{3}'),
    ({'case': token.Case.LowerCamel, 'padding': (3, 3)}, '[a-z][a-zA-Z]{2}'),
    ({'case': token.Case.UpperCamel, 'padding': (3, 3)}, '[A-Z][a-zA-Z]{2}'),

    ({'case': token.Case.Lower, 'padding': (1, 3)}, '[a-z]{1,3}'),
    ({'case': token.Case.Upper, 'padding': (1, 3)}, '[A-Z]{1,3}'),
    ({'case': token.Case.LowerCamel, 'padding': (1, 3)}, '[a-z][a-zA-Z]{1,2}'),
    ({'case': token.Case.UpperCamel, 'padding': (1, 3)}, '[A-Z][a-zA-Z]{1,2}'),

    ({'case': token.Case.Lower, 'numbers': True, 'padding': (1, 3)}, '[a-z][a-z0-9]{1,2}'),
    ({'case': token.Case.Upper, 'numbers': True, 'padding': (1, 3)}, '[A-Z][A-Z0-9]{1,2}'),
    ({'case': token.Case.LowerCamel, 'numbers': True, 'padding': (1, 3)}, '[a-z][a-zA-Z0-9]{1,2}'),
    ({'case': token.Case.UpperCamel, 'numbers': True, 'padding': (1, 3)}, '[A-Z][a-zA-Z0-9]{1,2}'),

    ({'case': token.Case.Lower, 'numbers': True, 'padding': (3, 0)}, '[a-z][a-z0-9]{2,}'),
    ({'case': token.Case.Upper, 'numbers': True, 'padding': (3, 0)}, '[A-Z][A-Z0-9]{2,}'),
    ({'case': token.Case.LowerCamel, 'numbers': True, 'padding': (3, 0)}, '[a-z][a-zA-Z0-9]{2,}'),
    ({'case': token.Case.UpperCamel, 'numbers': True, 'padding': (3, 0)}, '[A-Z][a-zA-Z0-9]{2,}'),

    ({'case': token.Case.Lower, 'padding': (3, 0)}, '[a-z]{3,}'),
    ({'case': token.Case.Upper,  'padding': (3, 0)}, '[A-Z]{3,}'),
    ({'case': token.Case.LowerCamel, 'padding': (3, 0)}, '[a-z][a-zA-Z]{2,}'),
    ({'case': token.Case.UpperCamel, 'padding': (3, 0)}, '[A-Z][a-zA-Z]{2,}'),
))
def test_case_get_regex(kwargs, expected):
    assert token.Case.get_regex(**kwargs) == expected


@pytest.mark.parametrize('token_config, string, expected', (
    ({constants.TOKEN_TYPE: 'str', 'padding': None}, 'one', 'one'),
    ({constants.TOKEN_TYPE: 'str', 'padding': '3'}, 'abc', 'abc'),
    ({constants.TOKEN_TYPE: 'str', 'padding': '3+'}, 'abcde', 'abcde'),
    ({constants.TOKEN_TYPE: 'str', 'padding': '+3'}, 'ab', 'ab'),
    ({constants.TOKEN_TYPE: 'int', 'padding': None}, '1', 1),
    ({constants.TOKEN_TYPE: 'int', 'padding': None}, '0001', 1),
    ({constants.TOKEN_TYPE: 'int', 'padding': 4}, '0001', 1),
    ({constants.TOKEN_TYPE: 'float', 'padding': None}, '1.3', 1.3),
    ({constants.TOKEN_TYPE: 'float', 'padding': None}, '1.30000', 1.3),
    ({constants.TOKEN_TYPE: 'float', 'padding': 5}, '1.30000', 1.3),
    ({constants.TOKEN_TYPE: 'str', 'case': 'lower'}, 'abc', 'abc'),
    ({constants.TOKEN_TYPE: 'str', 'case': 'UPPER'}, 'ABC', 'ABC'),
    ({constants.TOKEN_TYPE: 'str', 'case': 'lowerCamel'}, 'abcDef', 'abcDef'),
    ({constants.TOKEN_TYPE: 'str', 'case': 'UpperCamel'}, 'AbcDef', 'AbcDef'),
    ({constants.TOKEN_TYPE: 'str', 'case': 'lower'}, 'abc1', 'abc1'),
    ({constants.TOKEN_TYPE: 'str', 'case': 'lower', 'padding': '3'}, 'abc', 'abc'),
    ({constants.TOKEN_TYPE: 'sequence'}, '50', 50),
    ({constants.TOKEN_TYPE: 'sequence'}, '###', '###'),
    ({constants.TOKEN_TYPE: 'sequence'}, '%04d', '%04d'),
    ({constants.TOKEN_TYPE: 'sequence', 'padding': '3+'}, '001', 1),
    ({constants.TOKEN_TYPE: 'sequence', 'padding': '3+'}, '###', '###'),
    ({constants.TOKEN_TYPE: 'sequence', 'padding': '3+'}, '%03d', '%03d'),
))
def test_parse(token_config, string, expected):
    token_obj = token.get_token('name', token_config)
    assert token_obj.parse(string) == expected


@pytest.mark.parametrize('token_config, string', (
    ({constants.TOKEN_TYPE: 'str'}, 'one/two'),                           # Invalid characters
    ({constants.TOKEN_TYPE: 'int'}, 'one'),                               # Wrong type
    ({constants.TOKEN_TYPE: 'sequence'}, 'abc'),                          # Wrong type
    ({constants.TOKEN_TYPE: 'int', 'padding': 3}, '0001'),                # Too much padding
    ({constants.TOKEN_TYPE: 'float', 'padding': 2}, '1.300'),             # Too much padding
    ({constants.TOKEN_TYPE: 'int', 'padding': 5}, '0001'),                # Not enough padding
    ({constants.TOKEN_TYPE: 'float', 'padding': 4}, '1.300'),             # Not enough padding
    ({constants.TOKEN_TYPE: 'sequence', 'padding': '3+'}, '50'),          # Not enough padding
    ({constants.TOKEN_TYPE: 'sequence', 'padding': '3+'}, '##'),          # Not enough padding
    ({constants.TOKEN_TYPE: 'sequence', 'padding': '3+'}, '%02d'),        # Not enough padding
    ({constants.TOKEN_TYPE: 'str', 'choices': ['two', 'three']}, 'one'),  # Invalid choice
    ({constants.TOKEN_TYPE: 'int', 'choices': [2, 3]}, '1'),              # Invalid choice
    ({constants.TOKEN_TYPE: 'float', 'choices': [2.0, 3.0]}, '1.0'),      # Invalid choice
    ({constants.TOKEN_TYPE: 'str', 'case': 'lower'}, 'aBc'),              # Invalid case
    ({constants.TOKEN_TYPE: 'str', 'case': 'UPPER'}, 'aBc'),              # Invalid case
    ({constants.TOKEN_TYPE: 'str', 'case': 'lowerCamel'}, 'Abc'),         # Invalid case
    ({constants.TOKEN_TYPE: 'str', 'case': 'UpperCamel'}, 'aBc'),         # Invalid case
    ({constants.TOKEN_TYPE: 'str', 'case': 'lower', 'numbers': False}, 'abc1'),  # Numbers disallowed
    ({constants.TOKEN_TYPE: 'str', 'case': 'lower', 'numbers': True}, '1abc'),   # Leading number
))
def test_parse_fail(token_config, string):
    token_obj = token.get_token('name', token_config)
    with pytest.raises(ParseError):
        token_obj.parse(string)


@pytest.mark.parametrize('token_config, value, expected', (
    ({constants.TOKEN_TYPE: 'str'}, 'one', 'one'),
    ({constants.TOKEN_TYPE: 'str'}, 1, '1'),
    ({constants.TOKEN_TYPE: 'int'}, 1, '1'),
    ({constants.TOKEN_TYPE: 'float'}, 1, '1.0'),
    ({constants.TOKEN_TYPE: 'sequence', 'padding': 3}, 1, '001'),
    ({constants.TOKEN_TYPE: 'float', 'padding': '3'}, 1, '1.000'),
    ({constants.TOKEN_TYPE: 'int', 'padding': '3'}, 1, '001'),
    ({constants.TOKEN_TYPE: 'int'}, constants.WILDCARD, constants.WILDCARD),
    ({constants.TOKEN_TYPE: 'int', 'padding': 3}, constants.WILDCARD, constants.WILDCARD_ONE * 3),
    ({constants.TOKEN_TYPE: 'str', 'case': token.Case.Lower}, 'ab', 'ab'),
    ({constants.TOKEN_TYPE: 'str', 'case': token.Case.Lower}, 'AB', 'ab'),
    ({constants.TOKEN_TYPE: 'str', 'case': token.Case.Upper}, 'AB', 'AB'),
    ({constants.TOKEN_TYPE: 'str', 'case': token.Case.Upper}, 'ab', 'AB'),
    ({constants.TOKEN_TYPE: 'str', 'case': token.Case.UpperCamel}, 'ab', 'Ab'),
    ({constants.TOKEN_TYPE: 'str', 'case': token.Case.LowerCamel}, 'Ab', 'ab'),
))
def test_format(token_config, value, expected):
    token_obj = token.get_token('name', token_config)
    assert token_obj.format(value) == expected


@pytest.mark.parametrize('token_config, value', (
    ({constants.TOKEN_TYPE: 'int'}, 'one'),                  # Wrong type
    ({constants.TOKEN_TYPE: 'str'}, 'one/two'),              # Invalid characters
    ({constants.TOKEN_TYPE: 'str', 'numbers': False}, '1'),  # Invalid characters
    ({constants.TOKEN_TYPE: 'str', 'padding': 3}, 'ab'),     # Not enough padding
    ({constants.TOKEN_TYPE: 'str', 'padding': 3}, 'abcd'),   # Too much padding
    ({constants.TOKEN_TYPE: 'str', 'choices': ['a', 'b', 'c']}, 'd'),  # Invalid choice
))
def test_format_fail(token_config, value):
    token_obj = token.get_token('name', token_config)
    with pytest.raises(FormatError):
        token_obj.format(value)


@pytest.mark.parametrize('cls, name', (
    (token.FloatToken, 'test'),
    (token.IntToken, 'test'),
    (token.StringToken, 'test'),
))
def test_name(cls, name):
    assert cls(name).name == name


@pytest.mark.parametrize('cls, name, default, value', (
    (token.FloatToken, 'test', '1.0', 1.0),
    (token.IntToken, 'test', '1', 1),
    (token.StringToken, 'test', 'one', 'one'),
))
def test_default(cls, name, default, value):
    assert cls(name, default=default).default == value


@pytest.mark.parametrize('cls, name, choices, values', (
    (token.FloatToken, 'test', ['1.0', '2.0'], [1.0, 2.0]),
    (token.IntToken, 'test', ['1', '2'], [1, 2]),
    (token.StringToken, 'test', ['one', 'two'], ['one', 'two']),
))
def test_choices(cls, name, choices, values):
    assert cls(name, choices=choices).choices == values


@pytest.mark.parametrize('padding, expected', (
    ('1', (1, 1)),
    ('3+', (3, 0)),
    ('+3', (1, 3)),
    (3, (3, 3)),
))
def test_padding(padding, expected):
    token_obj = token.get_token('name', {constants.TOKEN_TYPE: 'str', 'padding': padding})
    assert token_obj.padding == expected


def test_case():
    token_obj = token.get_token('test', {constants.TOKEN_TYPE: 'str', 'case': token.Case.LowerCamel})
    assert token_obj.case == token.Case.LowerCamel


def test_numbers():
    token_obj = token.get_token('test', {constants.TOKEN_TYPE: 'str', 'numbers': True})
    assert token_obj.numbers is True
