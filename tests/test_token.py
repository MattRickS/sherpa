import pytest

from sherpa.token import Token, IntToken, StringToken, FloatToken
from sherpa.exceptions import ParseError


@pytest.mark.parametrize('string_type, cls', (
    ('float', FloatToken),
    ('int', IntToken),
    ('str', StringToken),
))
def test_get_type(string_type, cls):
    assert Token.get_type(string_type) == cls


@pytest.mark.parametrize('token_type, string, value, padding', (
    ('str', 'one', 'one', None),
    ('int', '1', 1, None),
    ('int', '0001', 1, None),
    ('int', '0001', 1, 4),
    ('float', '1.3', 1.3, None),
    ('float', '1.30000', 1.3, None),
    ('float', '1.30000', 1.3, 5),
))
def test_parse(token_type, string, value, padding):
    cls = Token.get_type(token_type)
    token = cls('test', padding=padding)
    assert token.parse(string) == value


@pytest.mark.parametrize('token_type, string, choices, padding', (
    ('str', 'one/two', None, None),             # Invalid characters
    ('int', 'one', None, None),                 # Wrong type
    # ('int', '0001', None, 3),                   # Too much padding
    ('int', '0001', None, 5),                   # Not enough padding
    # ('float', '1.300', None, 2),                # Too much padding
    ('float', '1.300', None, 4),                # Not enough padding
    ('str', 'one', ['two', 'three'], None),     # Invalid choice
    ('int', '1', [2, 3], None),                   # Invalid choice
    ('float', '1.0', [2.0, 3.0], None),           # Invalid choice
))
def test_parse_fail(token_type, string, choices, padding):
    cls = Token.get_type(token_type)
    token = cls('test', choices=choices, padding=padding)
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
    assert cls(name, default).default == value


@pytest.mark.parametrize('cls, name, choices, values', (
    (FloatToken, 'test', ['1.0', '2.0'], [1.0, 2.0]),
    (IntToken, 'test', ['1', '2'], [1, 2]),
    (StringToken, 'test', ['one', 'two'], ['one', 'two']),
))
def test_choices(cls, name, choices, values):
    assert cls(name, choices=choices).choices == values


@pytest.mark.parametrize('cls, name, padding', (
    (FloatToken, 'test', 1),
    (IntToken, 'test', 2),
    (StringToken, 'test', 3),
))
def test_padding(cls, name, padding):
    assert cls(name, padding=padding).padding == padding
