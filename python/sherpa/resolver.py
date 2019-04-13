import os

import yaml
from sherpa import constants
from sherpa.exceptions import ParseError, TemplateResolverError
from sherpa.pathtemplate import PathTemplate
from sherpa.template import Template
from sherpa import token


class TemplateResolver(object):
    @classmethod
    def from_environment(cls):
        """
        Reads the environment variable for a file to load the configuration from

        :raise TemplateResolverError: if the environment variable is not set or
                                  set to a non-existent file
        :rtype: TemplateResolver
        """
        path = os.getenv(constants.ENV_VAR)
        if not path or not os.path.exists(path):
            raise TemplateResolverError(
                'Invalid environment path for TemplateResolver configuration: '
                '{}={}'.format(constants.ENV_VAR, path)
            )
        return cls.from_file(path)

    @classmethod
    def from_file(cls, filepath):
        """
        :param str  filepath:
        :rtype: TemplateResolver
        """
        with open(filepath) as f:
            config = yaml.load(f)
        return cls(config)

    def __init__(self, config):
        """
        :param dict[str, dict]  config:
        """
        self._config = config
        self._templates = {}
        self._tokens = {}

        # Ensure tokens are loaded and valid before loading templates
        for name in self._config[constants.KEY_TOKEN]:
            self._load_token(name)

        for template_type in (constants.KEY_NAMETEMPLATE, constants.KEY_PATHTEMPLATE):
            for name in self._config.get(template_type, ()):
                # Templates can reference other templates which recursively load,
                # avoid reloading already evaluated templates
                if name not in self._templates.get(template_type, ()):
                    self._load_template(template_type, name)

    @property
    def nametemplates(self):
        """
        :rtype: dict[str, Template]
        """
        return self._templates.get(constants.KEY_NAMETEMPLATE, {}).copy()

    @property
    def pathtemplates(self):
        """
        :rtype: dict[str, PathTemplate]
        """
        return self._templates.get(constants.KEY_PATHTEMPLATE, {}).copy()

    @property
    def tokens(self):
        """
        :rtype: dict[str, token.Token]
        """
        return self._tokens.copy()

    def fields_from_path(self, path):
        """
        Convenience method that calls parse_path and discards the template

        :param str  path:
        :rtype: dict
        """
        template, fields = self.parse_path(path)
        return fields

    def extract_closest_pathtemplate(self, path, directory=True):
        """
        Finds the template that extracts the greatest number of directories in 
        the path.
        
        :param str  path: 
        :param bool directory:  If True, partial matches are only considered if 
                                they match a full directory and not a partial 
                                folder/filename match. The returned relative 
                                path will strip any leading path separator.
        :rtype: tuple[Template, str, dict, str]
        :return: Tuple of (
            Template,
            matched section of path,
            matched token fields,
            relative remainder of path
        )
        """
        matches = {}
        for template in self._templates.get(constants.KEY_PATHTEMPLATE, {}).values():
            try:
                match_path, fields, relative = template.extract(path, directory=directory)
                matches[relative.count('/')] = (template, match_path, fields, relative)
            except ParseError:
                continue
        return matches[min(matches)]

    def get_nametemplate(self, template_name, allow_tokens=True):
        """
        :param str  template_name:  Name of the template to get
        :param bool allow_tokens:   Whether or not to use tokens for name
                                    templates if no template exists
        :rtype: Template
        """
        try:
            template = self._get_template(constants.KEY_NAMETEMPLATE, template_name)
        except KeyError:
            if not allow_tokens:
                raise
            token_obj = self._tokens[template_name]
            template = Template.from_token(token_obj)
        return template

    def get_pathtemplate(self, template_name):
        """
        :param str  template_name:
        :rtype: Template
        """
        return self._get_template(constants.KEY_PATHTEMPLATE, template_name)

    def get_token(self, token_name):
        """
        :param str  token_name:
        :rtype: token.Token
        """
        return self._tokens[token_name]

    def parse_path(self, path):
        """
        :param str  path:
        :rtype: tuple[Template, dict]
        :return: Tuple of (matching template object, dictionary of parsed fields)
        """
        for template in self._templates.get(constants.KEY_PATHTEMPLATE, {}).values():
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
        template = self._get_template(constants.KEY_PATHTEMPLATE, template_name)
        return template.paths(fields)

    def template_from_path(self, path):
        """
        Convenience method that calls parse_path and discards the fields

        :param str  path:
        :rtype: Template
        """
        template, fields = self.parse_path(path)
        return template

    def _get_template(self, template_type, template_name):
        template = self._templates.get(template_type, {}).get(template_name)
        # Templates can be recursive, load on demand
        if template is None:
            template = self._load_template(template_type, template_name)
        return template

    def _load_template(self, template_type, template_name):
        """
        :param str  template_type:
        :param str  template_name:
        :rtype: Template
        """
        template_string = self._config[template_type][template_name]

        tokens = {}
        parent = None
        relatives = []

        for match in constants.MATCH_PATTERN.finditer(template_string):
            reference_type, token_name = match.groups()
            if reference_type:
                # Extract parent and relative Templates by name
                template = self._get_template(template_type, token_name)
                if reference_type == constants.REF_PATHTEMPLATE and match.start() == 0:
                    parent = template
                else:
                    relatives.append(template)
            else:
                # Extract local tokens, validate against loaded Tokens
                tokens[token_name] = self._tokens[token_name]

        if template_type == constants.KEY_PATHTEMPLATE:
            template = PathTemplate(
                template_name,
                template_string,
                parent=parent,
                relatives=relatives,
                tokens=tokens
            )
        elif template_type == constants.KEY_NAMETEMPLATE:
            template = Template(template_name,
                                template_string,
                                relatives=relatives,
                                tokens=tokens)
        else:
            raise TypeError('Invalid template type: {}'.format(template_type))

        self._templates.setdefault(template_type, {})[template_name] = template
        return template

    def _load_token(self, token_name):
        """
        :param str  token_name:
        :rtype: token.Token
        """
        # Config is allowed to define a shorthand {name: type}, ensure it's in
        # dictionary format so that the keywords can be expanded to Token's init
        token_config = self._config[constants.KEY_TOKEN][token_name]
        if not isinstance(token_config, dict):
            token_config = {constants.TOKEN_TYPE: token_config}

        token_obj = token.get_token(token_name, token_config)
        self._tokens[token_name] = token_obj
        return token_obj
