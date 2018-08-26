import json

from .exceptions import ParseError
from .template import Template
from .token import Token, TOKEN_CLASS


TEMPLATE_KEY = 'templates'
TOKEN_KEY = 'tokens'

TOKEN_TYPE = 'type'
TOKEN_PADDING = 'padding'
TOKEN_VALUES = 'valid_values'
TOKEN_DEFAULT = 'default'


class PathResolver(object):
    @classmethod
    def from_file(cls, filepath):
        """
        :param str  filepath:
        :rtype: PathResolver
        """
        with open(filepath) as f:
            config = json.load(f)
        return cls(config)

    def __init__(self, config):
        """
        :param dict[str, dict]  config:
        """
        self._template_config = config[TEMPLATE_KEY]
        self._token_config = config[TOKEN_KEY]

        self._templates = {}
        self._tokens = {}

        for name in self._token_config:
            self._load_token(name)

        for name in self._template_config:
            self._load_template(name)

    @property
    def templates(self):
        """
        :rtype: dict[str, Template]
        """
        return self._templates

    @property
    def tokens(self):
        """
        :rtype: dict[str, Token]
        """
        return self._tokens

    def fields_from_path(self, path):
        """
        :param str  path:
        :rtype: dict
        """
        template, fields = self.parse_path(path)
        return fields

    def get_template(self, template_name):
        """

        :param str  template_name:
        :rtype: Template
        """
        template = self._templates.get(template_name)
        if template is None:
            template = self._load_template(template_name)
        return template

    def parse_path(self, path):
        """
        :param str  path:
        :rtype: tuple[Template, dict]
        """
        for template in self._templates.values():
            try:
                # To do closest, add regex pattern at end to catch all, and then compare to find the
                # shortest end point.
                fields = template.parse(path)
                return template, fields
            except ParseError:
                continue
        raise ParseError('No templates match the given path: {!r}'.format(path))

    def paths_from_template(self, template_name, fields):
        """
        :param str  template_name:
        :param dict fields:
        :rtype: list[str]
        """
        template = self._templates[template_name]
        return template.paths(fields)

    def template_from_path(self, path, closest=False):
        """
        :param str  path:
        :param bool closest:
        :rtype: Template
        """
        template, fields = self.parse_path(path)
        return template

    def _load_template(self, template_name):
        """
        :param str  template_name:
        :rtype: Template
        """
        template_string = self._template_config[template_name]
        template = Template.from_string(template_name, template_string, self)
        self._templates[template_name] = template
        return template

    def _load_token(self, token_name):
        """
        :param str  token_name:
        :rtype: Token
        """
        token_config = self._token_config[token_name]
        if not isinstance(token_config, dict):
            token_config = {TOKEN_TYPE: token_config}
        token_type = token_config.pop(TOKEN_TYPE, 'str')
        cls = TOKEN_CLASS.get(token_type)
        token = cls(token_name, **token_config)
        self._tokens[token_name] = token
        return token
