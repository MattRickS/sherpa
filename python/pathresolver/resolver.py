import os
import yaml

from pathresolver import constants
from pathresolver.exceptions import ParseError, PathResolverError
from pathresolver.template import Template
from pathresolver.token import Token


class PathResolver(object):
    @classmethod
    def from_environment(cls):
        """
        Reads the environment variable for a file to load the configuration from

        :raise PathResolverError: if the environment variable is not set or
                                  set to a non-existent file
        :rtype: PathResolver
        """
        path = os.getenv(constants.ENV_VAR)
        if not path or not os.path.exists(path):
            raise PathResolverError(
                'Invalid environment path for pathresolver configuration: '
                '{}={}'.format(constants.ENV_VAR, path)
            )
        return cls.from_file(path)

    @classmethod
    def from_file(cls, filepath):
        """
        :param str  filepath:
        :rtype: PathResolver
        """
        with open(filepath) as f:
            config = yaml.load(f)
        return cls(config)

    def __init__(self, config):
        """
        :param dict[str, dict]  config:
        """
        self._template_config = config[constants.TEMPLATE_KEY]
        self._token_config = config[constants.TOKEN_KEY]

        self._templates = {}
        self._tokens = {}

        # Ensure tokens are loaded and valid before loading templates
        for name in self._token_config:
            self._load_token(name)

        for name in self._template_config:
            # Templates can reference other templates which recursively load,
            # avoid reloading already evaluated templates
            if name not in self._templates:
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
        # Templates can be recursive, load on demand
        if template is None:
            template = self._load_template(template_name)
        return template

    def parse_path(self, path):
        """
        :param str  path:
        :rtype: tuple[Template, dict]
        :return: Tuple of (matching template object, dictionary of parsed fields)
        """
        for template in self._templates.values():
            try:
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

    def template_from_path(self, path):
        """
        :param str  path:
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
        # Pass in self so that the template can pull tokens and any recursive
        # templates
        template = Template.from_string(template_name, template_string, self)
        self._templates[template_name] = template
        return template

    def _load_token(self, token_name):
        """
        :param str  token_name:
        :rtype: Token
        """
        # Config is allowed to define a shorthand {name: type}, ensure it's in
        # dictionary format so that the keywords can be expanded to Token's init
        token_config = self._token_config[token_name]
        if not isinstance(token_config, dict):
            token_config = {constants.TOKEN_TYPE: token_config}

        # Pop the type key so that it's not passed to Token's init
        token_type = token_config.pop(constants.TOKEN_TYPE, 'str')
        cls = Token.get_type(token_type)
        if cls is None:
            raise ParseError('Unknown token type for {!r}: {}'.format(
                token_name, token_type
            ))

        # Let Token validate itself, will raise any errors
        token = cls(token_name, **token_config)
        self._tokens[token_name] = token
        return token
