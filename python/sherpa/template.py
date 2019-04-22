import re
from collections import Iterable

from sherpa import constants
from sherpa.exceptions import FormatError, ParseError, TemplateValidationError
from sherpa.token import Token


class Template(object):
    SYMBOL = constants.REF_NAMETEMPLATE

    @classmethod
    def from_token(cls, token):
        """
        Converts a token to a simple template

        :param Token token:
        :rtype: Template
        """
        return cls(token.name, '{%s}' % token.name, tokens=(token,))

    def __init__(self, name, config_string, relatives=None, tokens=None):
        """
        :param str                  name:
        :param str                  config_string:
        :param Iterable[Template]   relatives:
        :param Iterable[Token]      tokens:
        """
        self._name = name
        self._config_string = config_string
        self._relatives = tuple(relatives or ())
        self._local_tokens = {t.name: t for t in tokens or ()}

        self._ordered_fields = None     # type: tuple
        self._pattern = None            # type: str
        self._regex = None              # type: str
        self._tokens = None             # type: dict

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
            self._resolve_pattern()
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
        config_string = '{%s%s}' % (self.SYMBOL, self.name)
        if isinstance(template, Template):
            relatives = (self, template)
            name = template.name
            config_string += '{%s%s}' % (template.SYMBOL, template.name)
        elif isinstance(template, str):
            relatives = (self,)
            name = template
            config_string += template
        else:
            raise TypeError(
                'Cannot join unsupported datatype: {}'.format(type(template))
            )

        joined_template = self.__class__(self._name + '/' + name,
                                         config_string,
                                         relatives=relatives)
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
            if field in tokens:
                parsed = tokens[field].parse(value)
            else:
                parsed = value
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
        regex_segments = []
        pattern_segments = []
        for match in constants.PATTERN_MATCH.finditer(self._config_string):
            # We only care about templates, preserve token patterns
            template_type, name = match.groups()
            if not template_type:
                ordered_fields.append(name)
                continue
            elif template_type == constants.REF_NAMETEMPLATE:
                ordered_fields.append(name)
                regex_segments.append('(')

            # Rebuild this template's string by cutting at the indices for
            # any template reference, preserving the part that belongs to
            # this template and replacing the reference segment with the
            # target template's pattern.
            start, end = match.span()
            relative_template = linked_templates[name]
            ordered_fields += relative_template.ordered_fields
            segments = (self._config_string[last_idx:start], relative_template.pattern)
            pattern_segments.extend(segments)
            regex_segments.extend(segments)
            last_idx = end

            if template_type == constants.REF_NAMETEMPLATE:
                regex_segments.append(')')

        # Add any remaining string
        pattern_segments.append(self._config_string[last_idx:])
        self._pattern = ''.join(pattern_segments)
        self._ordered_fields = tuple(ordered_fields)

        regex_segments.append(self._config_string[last_idx:])
        regex_tokens = {token.name: '({})'.format(token.regex)
                        for token in self._get_tokens().values()}
        self._regex = ''.join(regex_segments).format(**regex_tokens)


class NameTemplate(Template):
    def __init__(self, name, config_string, relatives=None, tokens=None):
        if constants.PATTERN_NAMETEMPLATE_BLACKLIST.search(config_string):
            raise TemplateValidationError('Name templates cannot contain path separators')
        super(NameTemplate, self).__init__(name, config_string, relatives=relatives, tokens=tokens)
