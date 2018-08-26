from pathresolver.token import StringToken, IntToken
from pathresolver.template import Template
from pathresolver.exceptions import FormatError, ParseError


def test_template():
    project_token = StringToken('project')
    storage_token = StringToken('storage', default='prod', valid_values=['prod', '.config', 'dev'])
    division_token = StringToken('division')
    entity_token = StringToken('entity', default='this')

    project_template = Template('project',
                                'D:/Programming/pathresolver/tests/mocks/projects/{project}',
                                tokens={'project': project_token})
    division_template = Template('division',
                                 '@{project}/{storage}/{division}',
                                 parent=project_template,
                                 tokens={'division': division_token, 'storage': storage_token})
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


if __name__ == '__main__':
    test_template()
