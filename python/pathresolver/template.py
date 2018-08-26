import glob
import os
import re

from .exceptions import FormatError, ParseError
from .tokens import Token, WILDCARD

MATCH_PATTERN = re.compile('(@)?{(\w+)}')


class Template(object):
    @classmethod
    def from_string(cls, name, path, resolver):
        """
        :param str          name:
        :param str          path:
        :param PathResolver resolver:
        :rtype: Template
        """
        tokens = {}
        parent = None
        relatives = []

        for match in MATCH_PATTERN.finditer(path):
            is_template, token_name = match.groups()
            if is_template:
                # Extract parent and relative Templates by name
                template = resolver.get_template(token_name)
                if match.start() == 0:
                    parent = template
                else:
                    relatives.append(template)
            else:
                # Extract local tokens, validate against loaded Tokens
                tokens[token_name] = resolver.tokens[token_name]
        return cls(name, path, parent=parent, relatives=relatives, tokens=tokens)

    def __init__(self, name, path, parent=None, relatives=None, tokens=None):
        """
        :param str              name:
        :param str              path:
        :param Template         parent:
        :param list[Template]   relatives:
        :param dict[str, Token] tokens:
        """
        self._name = name
        self._path = path
        self._parent = parent
        self._relatives = relatives or []
        self._local_tokens = tokens

        self._pattern = None
        self._tokens = None

    def __repr__(self):
        return 'Template({!r}, {!r}, parent={}, relatives={}, tokens={})'.format(
            self._name, self._path, self._parent, self._relatives, self._local_tokens
        )

    def __str__(self):
        return '{}({})'.format(self._name, self.pattern)

    @property
    def name(self):
        """
        :rtype: str
        """
        return self._name

    @property
    def parent(self):
        """
        :rtype: Template
        """
        return self._parent

    @property
    def pattern(self):
        """
        :rtype: str
        """
        if self._pattern is None:
            # Assemble all the patterns required by the template
            linked_patterns = {t.name: t.pattern for t in self._relatives}
            if self._parent:
                linked_patterns[self._parent.name] = self._parent.pattern

            # Iterate over the linked templates to assemble the pattern
            last_idx = 0
            self._pattern = ''
            for match in MATCH_PATTERN.finditer(self._path):
                is_template, name = match.groups()
                if not is_template:
                    continue

                # Add any intermediate path and the template pattern
                start, end = match.span()
                self._pattern += self._path[last_idx:start] + linked_patterns[name]
                last_idx = end

            # Add any remaining path
            self._pattern += self._path[last_idx:]
        return self._pattern

    @property
    def regex(self):
        """
        :rtype: str
        """
        regex_tokens = {t.name: '(?P<{}>{})'.format(t.name, t.regex) for t in
                        self._get_tokens().values()}
        regex_pattern = '^' + self.pattern.format(**regex_tokens) + '$'
        return regex_pattern

    @property
    def relatives(self):
        """
        :rtype: list[Template]
        """
        return self._relatives

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
            value = fields.get(name)
            value = token.default if value is None else token.format(value)
            if value is None:
                missing.append(name)
            else:
                tokens[name] = value
        if missing:
            raise FormatError('Missing required fields for template {}: {}'.format(
                self, missing
            ))
        return self.pattern.format(**tokens)

    def missing(self, fields, ignore_defaults=True):
        """
        :param      fields:             Any iterable of strings
        :param bool ignore_defaults:    Ignores missing fields if a default value is available
        :rtype: dict[str, Token]
        """
        return {f: t for f, t in self._get_tokens().items() if
                f not in fields and (ignore_defaults or t.default is not None)}

    def parse(self, path):
        """converts path to dict to fields"""
        # Regex pattern
        match = re.match(self.regex, path)
        if not match:
            raise ParseError('Path {!r} does not match Template: {}'.format(path, self))

        fields = {token: self._tokens[token].parse(value) for token, value in
                  match.groupdict().items()}
        return fields

    def paths(self, fields, use_defaults=False):
        """
        Returns the paths on disk that match the given fields by using wildcards
        for missing values.

        :param dict fields:         Dictionary of fields and their values
        :param bool use_defaults:   Whether or not to use default token values
                                    for missing fields instead of wildcards.
        :rtype: list[str]
        """
        tokens = fields.copy()
        for f, t in self.missing(fields, ignore_defaults=True).items():
            tokens[f] = (t.default if use_defaults else None) or WILDCARD

        # tokens = {f: WILDCARD for f in self.missing(fields, ignore_defaults=not use_defaults)}
        # tokens.update(fields)

        pattern = self.format(tokens)
        return [os.path.normpath(p) for p in glob.iglob(pattern)]

    def _get_tokens(self):
        """
        :rtype: dict[str, Token]
        """
        if self._tokens is None:
            tokens = self._local_tokens.copy() if self._local_tokens else {}
            if self._parent:
                tokens.update(self._parent.tokens)
            self._tokens = tokens
        return self._tokens
