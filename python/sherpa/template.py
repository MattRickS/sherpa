import re

from sherpa import constants
from sherpa.exceptions import FormatError, ParseError
from sherpa.token import Token


class Template(object):
    def __init__(self, name, config_string, relatives=None, tokens=None):
        """
        :param str              name:
        :param str              config_string:
        :param list[Template]   relatives:
        :param dict[str, Token] tokens:
        """
        self._name = name
        self._config_string = config_string
        self._relatives = tuple(relatives or ())
        self._local_tokens = tokens

        self._ordered_fields = None     # type: tuple[Token]
        self._pattern = None            # type: str
        self._regex = None              # type: str
        self._tokens = None             # type: dict[str, Token]

    def __repr__(self):
        return 'Template({!r}, {!r}, relatives={}, tokens={})'.format(
            self._name, self._config_string, self._relatives, self._local_tokens
        )

    def __str__(self):
        return '{}({})'.format(self._name, self.pattern)

    @property
    def linked_templates(self):
        """
        All immediate templates linked to this template.

        :rtype: list[Template]
        """
        return self._relatives[:]

    @property
    def name(self):
        """
        :rtype: str
        """
        return self._name

    @property
    def ordered_fields(self):
        """
        Names of the tokens in the order they appear in the pattern

        :rtype: tuple[str]
        """
        if self._ordered_fields is None:
            self._resolve_pattern()
        return self._ordered_fields[:]

    @property
    def pattern(self):
        """
        Full template configuration pattern with relative templates expanded

        :rtype: str
        """
        if self._pattern is None:
            self._resolve_pattern()
        return self._pattern

    @property
    def regex(self):
        """
        Regex pattern used to match against strings

        :rtype: str
        """
        if self._regex is None:
            regex_tokens = {token.name: '({})'.format(token.regex)
                            for token in self._get_tokens().values()}
            self._regex = self.pattern.format(**regex_tokens)
        return self._regex

    @property
    def tokens(self):
        """
        :rtype: dict[str, Token]
        """
        return self._get_tokens().copy()

    def format(self, fields):
        """
        Formats the template pattern using the given fields. Missing fields use
        their default value if provided.

        :raise FormatError: if required fields are missing and no have no default
        :param dict fields:
        :rtype: str
        """
        missing = []
        tokens = {}
        for name, token in self._get_tokens().items():
            # Token default is the type value, not a string. Must still be formatted
            value = fields.get(name, token.default)
            if value is None:
                missing.append(name)
            else:
                tokens[name] = token.format(value)
        if missing:
            raise FormatError('Missing required fields for template {}: {}'.format(
                self, missing
            ))
        return self.pattern.format(**tokens)

    def join(self, template):
        """
        Appends the given template, returning a new Template object.
        Intended for combining relative templates on the fly.

        :param Template|str template: Suffix template or string
        :rtype: Template
        """
        tokens = self._local_tokens.copy()
        if isinstance(template, Template):
            relatives = self._relatives + template.linked_templates
            tokens.update(template._local_tokens)
            name = template.name
            config_string = template._config_string
        elif isinstance(template, str):
            relatives = self._relatives
            name = template
            config_string = template
        else:
            raise TypeError(
                'Cannot join unsupported datatype: {}'.format(type(template))
            )

        joiner = '' if config_string.startswith('/') else '/'
        joined_template = self.__class__(self._name + '/' + name,
                                         self._config_string + joiner + config_string,
                                         relatives=relatives,
                                         tokens=tokens)
        return joined_template

    def missing(self, fields, ignore_defaults=True):
        """
        :param      fields:             Any iterable of strings
        :param bool ignore_defaults:    Ignores missing fields if a default
                                        value is available
        :rtype: dict[str, Token]
        """
        return {f: t for f, t in self._get_tokens().items()
                if f not in fields and (ignore_defaults or t.default is not None)}

    def parse(self, string):
        """
        Parses the string against the pattern, extracting a dictionary of the
        fields and their values.

        :raise ParseError: if the string doesn't match the template's pattern
        :param str  string:
        :rtype: dict[str, object]
        """
        _, fields = self._parse(string, '^' + self.regex + '$')
        return fields

    def _get_tokens(self):
        """
        Lazy loads the full set of tokens used by this template's full pattern,
        ie, including the tokens of all referenced templates

        :rtype: dict[str, Token]
        """
        if self._tokens is None:
            tokens = self._local_tokens.copy() if self._local_tokens else {}
            for template in self.linked_templates:
                tokens.update(template.tokens)
            self._tokens = tokens
        return self._tokens

    def _parse(self, string, regex):
        # type: (str, str) -> tuple[re.Match, dict]
        """ Matches the pattern to the string, returning the match and fields """
        match = re.match(regex, string)
        if match is None:
            raise ParseError('String {!r} does not match Template: {}'.format(string, self))

        tokens = self._get_tokens()
        fields = {}
        for field, value in zip(self._ordered_fields, match.groups()):
            parsed = tokens[field].parse(value)
            existing = fields.get(field)
            if existing is not None and existing != parsed:
                raise ParseError('Different values for token: {} : ({}, {})'.format(
                    field, existing, parsed
                ))
            fields[field] = parsed

        return match, fields

    def _resolve_pattern(self):
        """ Extract the full pattern and ordered fields """
        # Assemble all the patterns required by the template
        linked_templates = {t.name: t for t in self.linked_templates}
        ordered_fields = []

        # Walk through this template's string and replace any references to
        # other templates with that template's pattern.
        last_idx = 0
        self._pattern = ''
        for match in constants.MATCH_PATTERN.finditer(self._config_string):
            # We only care about templates, preserve token patterns
            is_template, name = match.groups()
            if not is_template:
                ordered_fields.append(name)
                continue

            # Rebuild this template's string by cutting at the indices for
            # any template reference, preserving the part that belongs to
            # this template and replacing the reference segment with the
            # target template's pattern.
            start, end = match.span()
            relative_template = linked_templates[name]
            ordered_fields += relative_template.ordered_fields
            self._pattern += self._config_string[last_idx:start] + relative_template.pattern
            last_idx = end

        # Add any remaining string
        self._pattern += self._config_string[last_idx:]
        self._ordered_fields = tuple(ordered_fields)
