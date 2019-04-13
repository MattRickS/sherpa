import pytest

from sherpa import constants
from sherpa.token import get_token, IntToken, StringToken, FloatToken
from sherpa.exceptions import ParseError


@pytest.mark.parametrize('string_type, cls', (
    ('float', FloatToken),
    ('int', IntToken),
    ('str', StringToken),
))
def test_get_config(string_type, cls):
    assert get_token('name', {constants.TOKEN_TYPE: string_type}).__class__ == cls


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
    ({constants.TOKEN_TYPE: 'sequence'}, '50', 50),
    ({constants.TOKEN_TYPE: 'sequence'}, '###', '###'),
    ({constants.TOKEN_TYPE: 'sequence'}, '%04d', '%04d'),
    ({constants.TOKEN_TYPE: 'sequence', 'padding': '3+'}, '001', 1),
    ({constants.TOKEN_TYPE: 'sequence', 'padding': '3+'}, '###', '###'),
    ({constants.TOKEN_TYPE: 'sequence', 'padding': '3+'}, '%03d', '%03d'),
))
def test_parse(token_config, string, expected):
    token = get_token('name', token_config)
    assert token.parse(string) == expected


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
    token = get_token('name', token_config)
    with pytest.raises(ParseError):
        token.parse(string)


@pytest.mark.parametrize('cls, name', (
    (FloatToken, 'test'),
    (IntToken, 'test'),
    (StringToken, 'test'),
))
def test_name(cls, name):
    assert cls(name).name == name


@pytest.mark.parametrize('cls, name, default, value', (
    (FloatToken, 'test', '1.0', 1.0),
    (IntToken, 'test', '1', 1),
    (StringToken, 'test', 'one', 'one'),
))
def test_default(cls, name, default, value):
    assert cls(name, default=default).default == value


@pytest.mark.parametrize('cls, name, choices, values', (
    (FloatToken, 'test', ['1.0', '2.0'], [1.0, 2.0]),
    (IntToken, 'test', ['1', '2'], [1, 2]),
    (StringToken, 'test', ['one', 'two'], ['one', 'two']),
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
    token = get_token('name', {constants.TOKEN_TYPE: 'str', 'padding': padding})
    assert token.padding == expected
