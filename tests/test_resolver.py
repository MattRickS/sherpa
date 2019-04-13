import os
import shutil

import pytest

from sherpa import constants
from sherpa.resolver import TemplateResolver


@pytest.fixture(scope='module')
def mock_directory(request):
    return request.fspath.join('../mocks')


@pytest.fixture(scope='module')
def mock_config(mock_directory):
    return str(mock_directory.join('templates.yml'))


class MockFilesystem(object):
    def __init__(self, root):
        cfg = {
            constants.KEY_TOKEN: {
                'root': 'str',
                'storage': {
                    'type': 'str',
                    'default': 'active',
                    'choices': [
                        'active',
                        'archive',
                        'dev'
                    ]
                },
                'project': 'str',
                'category': 'str',
                'entity': 'str',
                'task': 'str',
                'extension': 'str',
                'metadata': 'str',
                'publish_type': {
                    'type': 'str',
                    'choices': [
                        'eggs',
                        'spam',
                    ]
                },
                'version': {
                    'type': 'int',
                    'padding': 3
                }
            },
            constants.KEY_PATHTEMPLATE: {
                'root': root,
                'project': '{@root}/{project}',
                'storage': '{@project}/{storage}',
                'category': '{@storage}/{category}',
                'entity': '{@category}/{entity}',
                'entity_data': '{@entity}/{metadata}.json',
                'publish': '{@entity}/publishes/{publish_type}/v{version}/{entity}_{publish_type}_v{version}.{extension}',
                'work': '{@entity}/work/{task}/workfile.{extension}'
            }
        }

        relative_directories = {
            'projectA': {
                'template': 'project',
                'fields': {
                    'project': 'projectA',
                },
            },
            'projectA/active': {
                'template': 'storage',
                'fields': {
                    'project': 'projectA',
                    'storage': 'active',
                }
            },
            'projectA/active/categoryA': {
                'template': 'category',
                'fields': {
                    'project': 'projectA',
                    'storage': 'active',
                    'category': 'categoryA',
                }
            },
            'projectA/active/categoryB': {
                'template': 'category',
                'fields': {
                    'project': 'projectA',
                    'storage': 'active',
                    'category': 'categoryB',
                }
            },
            'projectA/active/categoryA/entityA': {
                'template': 'entity',
                'fields': {
                    'project': 'projectA',
                    'storage': 'active',
                    'category': 'categoryA',
                    'entity': 'entityA',
                }
            },
            'projectA/active/categoryA/entityA/publishes/spam/v001/entityA_spam_v001.txt': {
                'template': 'publish',
                'fields': {
                    'project': 'projectA',
                    'storage': 'active',
                    'category': 'categoryA',
                    'entity': 'entityA',
                    'publish_type': 'spam',
                    'version': 1,
                    'extension': 'txt'
                }
            },
            'projectA/active/categoryA/entityA/publishes/eggs/v001/entityA_eggs_v001.txt': {
                'template': 'publish',
                'fields': {
                    'project': 'projectA',
                    'storage': 'active',
                    'category': 'categoryA',
                    'entity': 'entityA',
                    'publish_type': 'eggs',
                    'version': 1,
                    'extension': 'txt'
                }
            },
            'projectA/active/categoryA/entityA/publishes/eggs/v002/entityA_eggs_v002.txt': {
                'template': 'publish',
                'fields': {
                    'project': 'projectA',
                    'storage': 'active',
                    'category': 'categoryA',
                    'entity': 'entityA',
                    'publish_type': 'eggs',
                    'version': 2,
                    'extension': 'txt'
                }
            },
            'projectA/dev/categoryA/entityA/publishes/eggs/v001/entityA_eggs_v001.txt': {
                'template': 'publish',
                'fields': {
                    'project': 'projectA',
                    'storage': 'dev',
                    'category': 'categoryA',
                    'entity': 'entityA',
                    'publish_type': 'eggs',
                    'version': 1,
                    'extension': 'txt'
                }
            },
            'projectA/active/categoryA/entityB/publishes/spam/v001/entityB_spam_v001.txt': {
                'template': 'publish',
                'fields': {
                    'project': 'projectA',
                    'storage': 'active',
                    'category': 'categoryA',
                    'entity': 'entityB',
                    'publish_type': 'spam',
                    'version': 1,
                    'extension': 'txt'
                }
            },
            'projectA/active/categoryB/entityC/publishes/eggs/v001/entityC_eggs_v001.txt': {
                'template': 'publish',
                'fields': {
                    'project': 'projectA',
                    'storage': 'active',
                    'category': 'categoryB',
                    'entity': 'entityC',
                    'publish_type': 'eggs',
                    'version': 1,
                    'extension': 'txt'
                }
            },
            'projectA/active/categoryA/entityA/work/taskA/workfile.txt': {
                'template': 'work',
                'fields': {
                    'project': 'projectA',
                    'storage': 'active',
                    'category': 'categoryA',
                    'entity': 'entityA',
                    'task': 'taskA',
                    'extension': 'txt'
                }
            },
            'projectA/active/categoryA/entityB/work/taskB/workfile.txt': {
                'template': 'work',
                'fields': {
                    'project': 'projectA',
                    'storage': 'active',
                    'category': 'categoryA',
                    'entity': 'entityB',
                    'task': 'taskB',
                    'extension': 'txt'
                }
            },
            'projectA/active/categoryB/entityC/work/taskA/workfile.txt': {
                'template': 'work',
                'fields': {
                    'project': 'projectA',
                    'storage': 'active',
                    'category': 'categoryB',
                    'entity': 'entityC',
                    'task': 'taskA',
                    'extension': 'txt'
                }
            },
            'projectA/dev/categoryB/entityC/work/taskA/workfile.txt': {
                'template': 'work',
                'fields': {
                    'project': 'projectA',
                    'storage': 'dev',
                    'category': 'categoryB',
                    'entity': 'entityC',
                    'task': 'taskA',
                    'extension': 'txt'
                }
            },
        }

        self.root = root
        self.filepaths = {os.path.normpath(os.path.join(root, path)): fields
                          for path, fields in relative_directories.items()}
        self.resolver = TemplateResolver(cfg)

    def create(self):
        for filepath in self.filepaths:
            # Create the missing directories
            dirname = os.path.dirname(filepath)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            # Create the file
            if filepath.endswith('.txt'):
                with open(filepath, 'w+'):
                    pass

    def remove(self):
        shutil.rmtree(self.root)


@pytest.fixture(scope='module')
def mock_filesystem(mock_directory):
    root = str(mock_directory.join('/projects')).replace('\\', '/')
    filesystem = MockFilesystem(root)

    filesystem.create()
    yield filesystem
    filesystem.remove()


def test_from_environment(mock_config):
    os.environ[constants.ENV_VAR] = mock_config
    assert TemplateResolver.from_environment()


def test_from_file(mock_config):
    assert TemplateResolver.from_file(mock_config)


def test_parse_path(mock_filesystem):
    for filepath, data in mock_filesystem.filepaths.items():
        template, fields = mock_filesystem.resolver.parse_path(filepath)
        assert template.name == data['template']
        assert fields == data['fields']


def test_format_path(mock_filesystem):
    for filepath, data in mock_filesystem.filepaths.items():
        template = mock_filesystem.resolver.get_pathtemplate(data['template'])
        path = template.format(data['fields']).replace('/', os.path.sep)
        assert path == filepath


@pytest.mark.parametrize('template_name, fields', (
    ('project', {}),
    ('category', {'storage': 'active'}),
    ('entity', {'storage': 'active', 'category': 'categoryA', 'entity': 'entityA'}),
))
def test_paths(mock_filesystem, template_name, fields):
    template = mock_filesystem.resolver.get_pathtemplate(template_name)
    paths = [f for f, d in mock_filesystem.filepaths.items() if template_name == d['template']]
    assert template.paths(fields) == paths


@pytest.mark.parametrize('field, fields, values', (
    ('version', {'storage': 'active', 'category': 'categoryA', 'entity': 'entityA', 'publish_type': 'eggs'}, [1, 2]),
    ('version', {'storage': 'active', 'category': 'categoryA', 'entity': 'entityA', 'publish_type': 'spam'}, [1]),
    ('version', {'storage': 'active', 'category': 'categoryA', 'entity': 'entityB', 'publish_type': 'spam'}, [1]),
))
def test_values_from_paths(mock_filesystem, field, fields, values):
    template = mock_filesystem.resolver.get_pathtemplate('publish')
    assert list(template.values_from_paths(field, fields)) == values


@pytest.mark.parametrize('path, directory, template, start, end', (
    ('/projects/path/to/something', True, 'sequence', '/projects/path/to/something', ''),
    ('/projects/path/to/something.ext', True, 'storage', '/projects/path/to', 'something.ext'),
    ('/projects/path/to/something.ext', False, 'sequence', '/projects/path/to/something', '.ext'),
))
def test_extract_closest_template(path, directory, template, start, end):
    pr = TemplateResolver({
        'tokens': {
            'project': 'str',
            'storage': 'str',
            'sequence': 'str',
        },
        'templates': {
            'root': '/projects',
            'project': '{@root}/{project}',
            'storage': '{@project}/{storage}',
            'sequence': '{@storage}/{sequence}',
        }
    })
    results = pr.extract_closest_pathtemplate(path, directory=directory)
    template = pr.get_pathtemplate(template)
    assert results[0] == template
    assert results[1] == start
    assert results[3] == end
