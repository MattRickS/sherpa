from pathresolver.tokens import StringToken, IntToken
from pathresolver.template import Template
from pathresolver.resolver import PathResolver, TOKEN_KEY, TEMPLATE_KEY
from pathresolver.exceptions import FormatError, ParseError


def test_int():
    cfg_int = """
    tokens:
        int1: int
        int2:
            type: int
            default: 2
        int3:
            type: int
            choices: [1, 2, 3, 4]
        int4:
            type: int
            choices: [1, 2, 3, 4]
            default: 4
        int5:
            type: int
            choices: [1, 2, 3, 4]
            default: 5
    """

    itoken = IntToken('int', padding=3)
    assert itoken.format(1) == '001'
    assert itoken.parse('001') == 1

    # Invalid padding
    try:
        itoken.parse('1')
        assert False
    except ParseError:
        pass

    itoken = IntToken('int', valid_values=['1', '2', '3'])
    assert itoken.parse('3') == 3
    try:
        itoken.parse('4')
        assert False
    except ParseError:
        pass

    itoken = IntToken('int', default='2', valid_values=['1', '2', '3'])

    try:
        itoken = IntToken('int', default='0', valid_values=['1', '2', '3'])
        assert False
    except ValueError:
        pass


def test_template():
    project_token = StringToken('project')
    division_token = StringToken('division')
    entity_token = StringToken('entity', default='this')

    project_template = Template('project',
                                'D:/Programming/pathresolver/tests/mocks/projects/{project}',
                                tokens={'project': project_token})
    division_template = Template('division',
                                 '@{project}/{division}',
                                 parent=project_template,
                                 tokens={'division': division_token})
    entity_template = Template('entity',
                               '@{division}/{entity}',
                               parent=division_template,
                               tokens={'entity': entity_token})

    print(project_template.pattern)
    print(division_template.pattern)
    print(entity_template.pattern)

    print(project_template.parse('D:/Programming/pathresolver/tests/mocks/projects/banana'))

    print(project_template.regex)
    print(division_template.regex)
    print(entity_template.regex)

    print(project_template.format({'project': 'test'}))
    print(division_template.format({'project': 'test', 'division': 'divide'}))
    print(entity_template.format({'project': 'test', 'division': 'divide'}))
    try:
        print('FAIL:', division_template.format({'project': 'test'}))
    except FormatError:
        pass

    print(division_template.missing(['project']))
    print(division_template.missing({'division': 'test'}))
    print(entity_template.missing({'division': 'test'}))
    print(entity_template.missing({'division': 'test'}, ignore_defaults=False))

    print(entity_template.paths({
        'project': 'projectA',
        'division': 'asset_type',
        # entity has default
    }))
    print(entity_template.paths({
        'project': 'projectA',
        'division': 'asset_type',
        # entity has default
    }, use_defaults=True))
    print(entity_template.paths({
        # project has NO default
        'division': 'asset_type',
        'entity': 'assetA',
    }))


def test_resolver():
    cfg = {
        TOKEN_KEY: {
            'root': 'str',
            'storage': {
                'type': 'str',
                'default': 'prod',
                'valid_values': [
                    'prod',
                    '.config',
                    'dev'
                ]
            },
            'project': 'str',
            'division': 'str',
            'entity': 'str',
        },
        TEMPLATE_KEY: {
            'root': 'D:/Programming/pathresolver/tests/mocks/projects',
            'project': '@{root}/{project}',
            'storage': '@{project}/{storage}',
            'division': '@{storage}/{division}',
            'entity': '@{division}/{entity}',
        }
    }

    resolver = PathResolver(cfg)

    print(resolver.paths_from_template('project', {'project': 'projectA'}))
    print(resolver.paths_from_template('storage', {'project': 'projectA'}))
    print(resolver.template_from_path('D:/Programming/pathresolver/tests/mocks/projects/projectA/dev'))
    print(resolver.fields_from_path('D:/Programming/pathresolver/tests/mocks/projects/projectA/dev'))
    print(resolver.paths_from_template('entity', {'entity': 'assetA'}))


if __name__ == '__main__':
    test_int()
    test_template()
    test_resolver()
