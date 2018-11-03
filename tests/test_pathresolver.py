import os
import shutil

import pytest

from sherpa import constants
from sherpa.resolver import PathResolver


@pytest.fixture(scope='module')
def mock_directory(request):
    return request.fspath.join('../mocks')


@pytest.fixture(scope='module')
def mock_config(mock_directory):
    return str(mock_directory.join('templates.yml'))


class MockFilesystem(object):
    def __init__(self, root):
        cfg = {
            constants.TOKEN_KEY: {
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
            constants.TEMPLATE_KEY: {
                'root': root,
                'project': '@{root}/{project}',
                'storage': '@{project}/{storage}',
                'category': '@{storage}/{category}',
                'entity': '@{category}/{entity}',
                'publish': '@{entity}/publishes/{publish_type}/v{version}/{entity}_{publish_type}_v{version}.{extension}',
                'work': '@{entity}/work/{task}/workfile.{extension}'
            }
        }

        relative_directories = {
            'projectA': {
                'template': 'project',
                'fields': {
                    'project': 'projectA',
                }
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
        self.pathresolver = PathResolver(cfg)

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
    assert PathResolver.from_environment()


def test_from_file(mock_config):
    assert PathResolver.from_file(mock_config)


def test_parse_path(mock_filesystem):
    for filepath, data in mock_filesystem.filepaths.items():
        template, fields = mock_filesystem.pathresolver.parse_path(filepath)
        assert template.name == data['template']
        assert fields == data['fields']


def test_format_path(mock_filesystem):
    for filepath, data in mock_filesystem.filepaths.items():
        template = mock_filesystem.pathresolver.get_template(data['template'])
        path = template.format(data['fields']).replace('/', os.path.sep)
        assert path == filepath


@pytest.mark.parametrize('template_name, fields', (
    ('project', {}),
    ('category', {'storage': 'active'}),
    ('entity', {'storage': 'active', 'category': 'categoryA', 'entity': 'entityA'}),
))
def test_paths(mock_filesystem, template_name, fields):
    template = mock_filesystem.pathresolver.get_template(template_name)
    paths = [f for f, d in mock_filesystem.filepaths.items() if template_name == d['template']]
    assert template.paths(fields) == paths


@pytest.mark.parametrize('field, fields, values', (
    ('version', {'storage': 'active', 'category': 'categoryA', 'entity': 'entityA', 'publish_type': 'eggs'}, [1, 2]),
    ('version', {'storage': 'active', 'category': 'categoryA', 'entity': 'entityA', 'publish_type': 'spam'}, [1]),
    ('version', {'storage': 'active', 'category': 'categoryA', 'entity': 'entityB', 'publish_type': 'spam'}, [1]),
))
def test_values_from_paths(mock_filesystem, field, fields, values):
    template = mock_filesystem.pathresolver.get_template('publish')
    assert list(template.values_from_paths(field, fields)) == values
