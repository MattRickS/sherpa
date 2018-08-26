from pathresolver.resolver import PathResolver, TOKEN_KEY, TEMPLATE_KEY
from pathresolver.exceptions import FormatError, ParseError


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
            'version': {
                'type': 'int',
                'padding': 3
            }
        },
        TEMPLATE_KEY: {
            'root': 'D:/Programming/pathresolver/tests/mocks/projects',
            'project': '@{root}/{project}',
            'storage': '@{project}/{storage}',
            'division': '@{storage}/{division}',
            'entity': '@{division}/{entity}',
            'product': '@{entity}/products/v{version}'
        }
    }

    resolver = PathResolver(cfg)

    print(resolver.get_template('product').regex)

    print(resolver.paths_from_template('project', {'project': 'projectA'}))
    print(resolver.paths_from_template('storage', {'project': 'projectA'}))
    print(resolver.template_from_path('D:/Programming/pathresolver/tests/mocks/projects/projectA/dev'))
    print(resolver.fields_from_path('D:/Programming/pathresolver/tests/mocks/projects/projectA/dev'))
    print(resolver.paths_from_template('entity', {'entity': 'assetA'}))
    print(resolver.parse_path('D:/Programming/pathresolver/tests/mocks/projects/projectA/dev/asset_type/assetA/products/v001'))
    print(resolver.paths_from_template('product', {'entity': 'assetA'}))


if __name__ == '__main__':
    test_resolver()
