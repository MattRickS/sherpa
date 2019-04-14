from collections import namedtuple

import pytest

from sherpa import constants
from sherpa import exceptions
from sherpa import token
from sherpa.template import Template


MockTemplate = namedtuple('MockTemplate', 'template pattern linked tokens path fields')


@pytest.fixture(scope='module')
def mock_templates():
    token_config = {
        'one': {'type': 'int'},
        'two': {'type': 'int'},
        'a': {'type': 'str'},
        'b': {'type': 'str'},
        'c': {'type': 'str'},
        'f1': {'type': 'float'}
    }
    tokens = {name: token.get_token(name, config)
              for name, config in token_config.items()}

    def get_tokens(token_names):
        return [v for k, v in tokens.items() if k in token_names]

    pattern = '/scratch/{one}'
    tokens_a = get_tokens(('one', ))
    template_a = Template('templateA', pattern, tokens=tokens_a)
    mta = MockTemplate(template_a,
                       pattern=pattern,
                       linked=(),
                       tokens={t.name: t for t in tokens_a},
                       path='/scratch/1',
                       fields={'one': 1})

    pattern_b = '{#templateA}/{two}/{two}'
    tokens_b = get_tokens(('two', ))
    template_b = Template('templateB', pattern_b, relatives=(template_a,), tokens=tokens_b)
    tokens_b.extend(tokens_a)
    mtb = MockTemplate(template_b,
                       pattern='/scratch/{one}/{two}/{two}',
                       linked=(template_a,),
                       tokens={t.name: t for t in tokens_b},
                       path='/scratch/1/2/2',
                       fields={'one': 1, 'two': 2})

    pattern_c = 'relative/{a}/{b}'
    tokens_c = get_tokens(('a', 'b'))
    template_c = Template('templateC', pattern_c, tokens=tokens_c)
    mtc = MockTemplate(template_c,
                       pattern=pattern_c,
                       linked=(),
                       tokens={t.name: t for t in tokens_c},
                       path='relative/wordA/wordB',
                       fields={'a': 'wordA', 'b': 'wordB'})

    pattern_d = '/scratch/{f1}/{#templateC}'
    tokens_d = get_tokens(('f1', ))
    template_d = Template('templateD', pattern_d, relatives=(template_c,), tokens=tokens_d)
    tokens_d.extend(tokens_c)
    mtd = MockTemplate(template_d,
                       pattern='/scratch/{f1}/relative/{a}/{b}',
                       linked=(template_c,),
                       tokens={t.name: t for t in tokens_d},
                       path='/scratch/1.1/relative/wordA/wordB',
                       fields={'f1': 1.1, 'a': 'wordA', 'b': 'wordB'})

    return [mta, mtb, mtc, mtd]


def test_repr():
    template = Template('test', '/path/to/{test}', tokens=(token.get_token('test', {constants.TOKEN_TYPE: 'str'}),))
    assert repr(template) == (
        "Template('test', '/path/to/{test}', relatives=(), "
        "tokens={'test': StringToken('test', default=None, choices=None, padding=None)})"
    )


def test_pattern(mock_templates):
    for mock_template in mock_templates:
        assert mock_template.template.pattern == mock_template.pattern


def test_linked_templates(mock_templates):
    for mock_template in mock_templates:
        assert mock_template.template.linked_templates == mock_template.linked


def test_tokens(mock_templates):
    for mock_template in mock_templates:
        assert mock_template.template.tokens == mock_template.tokens


def test_format(mock_templates):
    for mock_template in mock_templates:
        assert mock_template.template.format(mock_template.fields) == mock_template.path


def test_parse(mock_templates):
    for mock_template in mock_templates:
        assert mock_template.template.parse(mock_template.path) == mock_template.fields


def test_parse_fail():
    template = Template('name', '/{token}/{token}',
                        tokens=(token.get_token('token', {constants.TOKEN_TYPE: 'str'}),))
    assert template.parse('/abc/abc') == {'token': 'abc'}
    with pytest.raises(exceptions.ParseError):
        template.parse('/abc/def')


def test_format_fail():
    template = Template('name', '/{foo}/{bar}',
                        tokens=(
                            token.get_token('foo', {constants.TOKEN_TYPE: 'str'}),
                            token.get_token('bar', {constants.TOKEN_TYPE: 'str'}),
                        ))
    assert template.format({'foo': 'foo', 'bar': 'bar'}) == '/foo/bar'
    with pytest.raises(exceptions.FormatError):
        template.format({'foo': 'foo'})


def test_from_token():
    token_obj = token.get_token('name', {constants.TOKEN_TYPE: 'str'})
    template = Template.from_token(token_obj)
    assert template.name == 'name'
    assert template.pattern == '{name}'
    assert template.tokens == {'name': token_obj}
