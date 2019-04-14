import os
from collections import namedtuple

import pytest

from sherpa import constants
from sherpa import token
from sherpa.pathtemplate import PathTemplate


MockTemplate = namedtuple('MockTemplate', 'template parent pattern relatives tokens path fields')


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
        return {k: v for k, v in tokens.items() if k in token_names}

    pattern = '/scratch/{one}'
    tokens_a = get_tokens(('one', ))
    template_a = PathTemplate('templateA', pattern, tokens=tokens_a)
    mta = MockTemplate(template_a,
                       parent=None,
                       pattern=pattern,
                       relatives=(),
                       tokens=tokens_a,
                       path='/scratch/1',
                       fields={'one': 1})

    pattern_b = '{@templateA}/{two}/{two}'
    tokens_b = get_tokens(('two', ))
    template_b = PathTemplate('templateB', pattern_b, parent=template_a, tokens=tokens_b.copy())
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
    template_c = PathTemplate('templateC', pattern_c, tokens=tokens_c)
    mtc = MockTemplate(template_c,
                       parent=None,
                       pattern=pattern_c,
                       relatives=(),
                       tokens=tokens_c,
                       path='relative/wordA/wordB',
                       fields={'a': 'wordA', 'b': 'wordB'})

    pattern_d = '/scratch/{f1}/{@templateC}'
    tokens_d = get_tokens(('f1', ))
    template_d = PathTemplate('templateD', pattern_d, relatives=[template_c], tokens=tokens_d.copy())
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


def test_extract(mock_templates, extra='sub/path'):
    for mock_template in mock_templates:
        expected = (mock_template.path, mock_template.fields, extra)
        path = '/'.join((mock_template.path, extra))
        assert mock_template.template.extract(path) == expected


def test_extract_specific():
    from sherpa.token import StringToken
    project_token = StringToken('project')
    project = PathTemplate('project', '/projects/{project}', tokens={'project': project_token})
    assert project.extract('/projects/path') == ('/projects/path', {'project': 'path'}, '')
    assert project.extract('/projects/path/to/something.ext') == ('/projects/path', {'project': 'path'}, 'to/something.ext')
    assert project.extract('/projects/path/to/something.ext', directory=False) == ('/projects/path', {'project': 'path'}, '/to/something.ext')


@pytest.mark.parametrize('token_configs, template_pattern, glob_pattern, paths, expected', (
    # Standard pattern and parse behaviour
    (
        {'project': {constants.TOKEN_TYPE: 'str'}, 'version': {constants.TOKEN_TYPE: 'int'}},
        '/project/{project}/v{version}',
        '/project/*/v*',
        ['/project/one/v001', '/project/one/v002', '/project/two/v001'],
        {os.path.normpath('/project/one/v001'): {'project': 'one', 'version': 1},
         os.path.normpath('/project/one/v002'): {'project': 'one', 'version': 2},
         os.path.normpath('/project/two/v001'): {'project': 'two', 'version': 1}}
    ),
    # Glob pattern uses multiple single wildcards for fixed padding length
    (
        {'project': {constants.TOKEN_TYPE: 'str', 'padding': '3'}},
        '/project/{project}',
        '/project/???',
        ['/project/one', '/project/two'],
        {os.path.normpath('/project/one'): {'project': 'one'},
         os.path.normpath('/project/two'): {'project': 'two'}}
    ),
    # Glob pattern with ranged padding should use generic wildcard and filter
    # the results with the correct regex pattern
    (
        {'project': {constants.TOKEN_TYPE: 'str', 'padding': '4+'}},
        '/project/{project}',
        '/project/*',
        ['/project/one', '/project/two', '/project/three'],
        {os.path.normpath('/project/three'): {'project': 'three'}}
    ),
))
def test_paths(mocker, token_configs, template_pattern, glob_pattern, paths, expected):
    mock = mocker.patch('glob.iglob', return_value=paths)
    tokens = {name: token.get_token(name, cfg) for name, cfg in token_configs.items()}
    template = PathTemplate('test', template_pattern, tokens=tokens)
    assert template.paths({}) == expected
    mock.assert_called_once_with(glob_pattern)
