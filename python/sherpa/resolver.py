import re

from sherpa import constants
from sherpa import exceptions
from sherpa import token
from sherpa.pathtemplate import PathTemplate
from sherpa.template import NameTemplate, Template


class TemplateResolver(object):
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
            except exceptions.ParseError:
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
        except exceptions.MissingTemplateError:
            if not allow_tokens:
                raise
            token_obj = self._tokens[template_name]
            template = NameTemplate.from_token(token_obj)
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

    def validate_unique_paths(self, raise_error=True):
        """
        Validates the each template pattern is unique. Returns a list of all
        groupings of template names which collide.

        Two templates are considered to be non-unique when their fixed path
        strings are identical, and all tokens could potentially resolve to the
        same values. Tokens that can resolve to the same value are pairings such
        as tokens of the same type, or an IntToken and a StringToken that allows
        numbers.

        Example:
            +----------+--------+--------+--------+--------+
            |          | token1 | token2 | token3 | token4 |
            +==========+========+========+========+========+
            |templateA |   X    |   X    |   X    |   X    |
            +----------+--------+--------+--------+--------+
            |templateB |   \-   |   X    |   X    |   X    |
            +----------+--------+--------+--------+--------+
            |templateC |   X    |   \-   |   \-   |   X    |
            +----------+--------+--------+--------+--------+

            The above would be valid, as although template A has a clash for
            every token, there is no one template that could match it.

        :raise TemplateValidationError: if any templates are not unique and
            raise_error is True
        :param bool raise_error: If True, raises TemplateValidationError for any
            conflicting templates
        :rtype: list[tuple[str, ...]]
        """
        # Validate that all patterns are unique.
        patterns = {}
        for template in self._templates[constants.KEY_PATHTEMPLATE].values():
            # Split the pattern by it's tokens, and extract the fixed path
            # segments to use as a unique key for the template. Map this key
            # to the ordered array of tokens.
            # Eg, {(path, ...): {template_name: (token, ...)}}
            parts = re.split('[{}]', template.pattern)
            fixed = tuple(parts[::2])
            ordered_tokens = tuple(self._tokens[name] for name in parts[1::2])
            patterns.setdefault(fixed, {})[template.name] = ordered_tokens

        # For any mapping that has multiple token sets, (ie, the fixed path
        # segments are identical, and the pattern only varies by tokens), check
        # if any of the tokens could possibly resolve the same value. If all
        # tokens could potentially resolve the same pattern, the template's are
        # not unique
        clashing_templates = []
        for data in patterns.values():
            # Must be at least two matching templates to possibly clash
            if len(data) < 2:
                continue
            # Split the data into two ordered lists
            template_names, token_sets = zip(*data.items())
            clashing = set()
            # Iterate over each set of tokens by index in which they appear
            for idx, tokens in enumerate(zip(*token_sets)):
                # Get a list of all groups of indexes that clash. These indexes
                # are their position in the ordered list of tokens, which is the
                # same order as the template names. Must be sorted to guarantee
                # sets can compare
                clashing_indexes = {tuple(sorted(indexes))
                                    for indexes in token.clashes(tokens).values()}
                # Only need to track clashes that are in ALL token sets, so if a
                # clash of indexes appears that hasn't clashed in previous
                # tokens, it can be ignored.
                # The exception is the first comparison which is the initial set
                # of clashing templates
                if idx == 0:
                    if not clashing_indexes:
                        break
                    clashing = clashing_indexes
                else:
                    clashing &= clashing_indexes
                if not clashing:
                    break

            # Any indexes which are still clashing at the end can be mapped to
            # their respective template names
            for indexes in clashing:
                clashing_templates.append(tuple(template_names[i] for i in indexes))

        if clashing_templates and raise_error:
            raise exceptions.TemplateValidationError(
                'Some templates can resolve to the same filepath: {}'.format(
                    clashing_templates
                )
            )

        return clashing_templates

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
        try:
            template_string = self._config[template_type][template_name]
        except KeyError:
            raise exceptions.MissingTemplateError(
                'Template {} {!r} does not exist'.format(
                    template_type, template_name
                )
            )

        tokens = []
        parent = None
        relatives = []

        for match in constants.PATTERN_MATCH.finditer(template_string):
            reference_type, token_name = match.groups()
            if reference_type == constants.REF_PATHTEMPLATE:
                # Extract parent and relative Templates by name
                template = self._get_template(constants.KEY_PATHTEMPLATE, token_name)
                if match.start() == 0:
                    parent = template
                else:
                    relatives.append(template)
            elif reference_type == constants.REF_NAMETEMPLATE:
                template = self._get_template(constants.KEY_NAMETEMPLATE, token_name)
                relatives.append(template)
            else:
                # Extract local tokens, validate against loaded Tokens
                try:
                    tokens.append(self._tokens[token_name])
                except KeyError:
                    raise exceptions.MissingTokenError(
                        'Token {!r} required by {} {!r} does not exist'.format(
                            token_name, template_type, template_name
                        )
                    )

        if template_type == constants.KEY_PATHTEMPLATE:
            template = PathTemplate(
                template_name,
                template_string,
                parent=parent,
                relatives=relatives,
                tokens=tokens
            )
        elif template_type == constants.KEY_NAMETEMPLATE:
            template = NameTemplate(template_name,
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
