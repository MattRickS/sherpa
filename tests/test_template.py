from collections import namedtuple

import pytest

from sherpa.token import Token
from sherpa.template import Template


MockTemplate = namedtuple('MockTemplate', 'template parent pattern relatives tokens path fields')


@pytest.fixture(scope='module')
def mock_templates():
    token_config = {
        'one': 'int',
        'two': 'int',
        'a': 'str',
        'b': 'str',
        'c': 'str',
        'f1': 'float'
    }
    tokens = {name: Token.get_type(token_type)(name)
              for name, token_type in token_config.items()}

    def get_tokens(token_names):
        return {k: v for k, v in tokens.items() if k in token_names}

    pattern = '/scratch/{one}'
    tokens_a = get_tokens(('one', ))
    template_a = Template('templateA', pattern, tokens=tokens_a)
    mta = MockTemplate(template_a,
                       parent=None,
                       pattern=pattern,
                       relatives=(),
                       tokens=tokens_a,
                       path='/scratch/1',
                       fields={'one': 1})

    pattern_b = '@{templateA}/{two}/{two}'
    tokens_b = get_tokens(('two', ))
    template_b = Template('templateB', pattern_b, parent=template_a, tokens=tokens_b.copy())
    tokens_b.update(tokens_a)
    mtb = MockTemplate(template_b,
                       parent=template_a,
                       pattern='/scratch/{one}/{two}/{two}',
                       relatives=(),
                       tokens=tokens_b,
                       path='/scratch/1/2/2',
                       fields={'one': 1, 'two': 2})

    pattern_c = 'relative/{a}/{b}'
    tokens_c = get_tokens(('a', 'b'))
    template_c = Template('templateC', pattern_c, tokens=tokens_c)
    mtc = MockTemplate(template_c,
                       parent=None,
                       pattern=pattern_c,
                       relatives=(),
                       tokens=tokens_c,
                       path='relative/wordA/wordB',
                       fields={'a': 'wordA', 'b': 'wordB'})

    pattern_d = '/scratch/{f1}/@{templateC}'
    tokens_d = get_tokens(('f1', ))
    template_d = Template('templateD', pattern_d, relatives=[template_c], tokens=tokens_d.copy())
    tokens_d.update(tokens_c)
    mtd = MockTemplate(template_d,
                       parent=None,
                       pattern='/scratch/{f1}/relative/{a}/{b}',
                       relatives=(template_c, ),
                       tokens=tokens_d,
                       path='/scratch/1.1/relative/wordA/wordB',
                       fields={'f1': 1.1, 'a': 'wordA', 'b': 'wordB'})

    return [mta, mtb, mtc, mtd]


def test_parent(mock_templates):
    for mock_template in mock_templates:
        assert mock_template.template.parent == mock_template.parent


def test_pattern(mock_templates):
    for mock_template in mock_templates:
        assert mock_template.template.pattern == mock_template.pattern


def test_relatives(mock_templates):
    for mock_template in mock_templates:
        assert mock_template.template.relatives == mock_template.relatives


def test_tokens(mock_templates):
    for mock_template in mock_templates:
        assert mock_template.template.tokens == mock_template.tokens


def test_format(mock_templates):
    for mock_template in mock_templates:
        assert mock_template.template.format(mock_template.fields) == mock_template.path


def test_parse(mock_templates):
    for mock_template in mock_templates:
        assert mock_template.template.parse(mock_template.path) == mock_template.fields


def test_extract(mock_templates, extra='/sub/path'):
    for mock_template in mock_templates:
        expected = (mock_template.path, mock_template.fields, extra)
        assert mock_template.template.extract(mock_template.path + extra) == expected
