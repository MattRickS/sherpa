import glob
import os
import re

from sherpa import constants
from sherpa.exceptions import FormatError, ParseError
from sherpa.token import Token


class Template(object):
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
        self._relatives = tuple(relatives or ())
        self._local_tokens = tokens

        self._ordered_fields = None     # type: tuple[Token]
        self._pattern = None            # type: str
        self._regex = None              # type: str
        self._tokens = None             # type: dict[str, Token]

    def __repr__(self):
        return 'Template({!r}, {!r}, parent={}, relatives={}, tokens={})'.format(
            self._name, self._path, self._parent, self._relatives, self._local_tokens
        )

    def __str__(self):
        return '{}({})'.format(self._name, self.pattern)

    @property
    def linked_templates(self):
        """
        All immediate templates linked to this template, relatives and parent.

        :rtype: list[Template]
        """
        return ((self._parent, ) if self._parent else ()) + self._relatives

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
    def parent(self):
        """
        The leading referenced template if one exists

        :rtype: Template
        """
        return self._parent

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
    def relatives(self):
        """
        All immediate linked templates that are not the parent, ie, that do not
        define the root of the path

        :rtype: tuple[Template]
        """
        return self._relatives

    @property
    def tokens(self):
        """
        :rtype: dict[str, Token]
        """
        return self._get_tokens().copy()

    def extract(self, path, directory=True):
        """
        Splits the path to the part that matches the template and the relative 
        remainder.
        
        :raise ParseError: if the path doesn't match the template's pattern
        :param str  path: 
        :param bool directory:  If True, a partial match is only considered if 
                                it matches a full directory and not a partial 
                                folder/filename match. The returned relative 
                                path will strip any leading path separator.
        :rtype: tuple[str, dict, str]
        """
        # If splitting by directory and the regex already includes a trailing 
        # separator, there is no need to modify the regex, otherwise ensure the 
        # pattern only matches if it's exact or followed by a directory separator
        modified = directory and not self.regex.endswith(os.path.sep)
        suffix = '(?:$|/)' if modified else ''
        regex = '^' + self.regex + suffix
        match, fields = self._parse(path, regex)
        start = match.group(0)
        # Extract the remainder before modifying the start path - this is 
        # because if splitting on the directory, the relative remainder should 
        # not include the leading separator.
        end = path[len(start):]
        # Only strip the captured separator if it was added to the pattern
        # Note, it's safe to use '/' instead of os.path.sep as the match is done 
        # against a separator replaced version of the path
        if modified and start.endswith('/'):
            start = start[:-1]
        return start, fields, end

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
            relatives = self._relatives + template.relatives
            if template.parent is not None:
                relatives = relatives + (template.parent,)

            tokens.update(template._local_tokens)
            name = template.name
            path = template._path
        elif isinstance(template, str):
            relatives = self._relatives
            name = template
            path = template
        else:
            raise TypeError(
                'Cannot join unsupported datatype: {}'.format(type(template))
            )

        joiner = '' if path.startswith('/') else '/'
        joined_template = Template(self._name + '/' + name,
                                   self._path + joiner + path,
                                   parent=self._parent,
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

    def parse(self, path):
        """
        Parses the path against the pattern, extracting a dictionary of the
        fields and their values.

        :raise ParseError: if the path doesn't match the template's pattern
        :param str  path:
        :rtype: dict[str, object]
        """
        _, fields = self._parse(path, '^' + self.regex + '$')
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
            # Default value might be None; in either case, fallback on wildcard
            tokens[f] = (t.default if use_defaults else None) or constants.WILDCARD

        pattern = self.format(tokens)
        return [os.path.normpath(p) for p in glob.iglob(pattern)]

    def values_from_paths(self, field, fields, use_defaults=False):
        """
        Finds all paths on disk that match the given fields and extracts the
        value for the requested field in each path.

        :param str                  field:
        :param dict[str, object]    fields:
        :param bool                 use_defaults:
        :rtype: dict[object, str]
        """
        fields[field] = constants.WILDCARD
        paths = self.paths(fields, use_defaults)
        path_fields = {self.parse(p)[field]: p for p in paths}
        return path_fields

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

    def _parse(self, path, regex):
        # type: (str, str) -> tuple[re.Match, dict]
        """ Matches the pattern to the path, returning the match and fields """
        path = path.replace(os.path.sep, '/')
        match = re.match(regex, path)
        if match is None:
            raise ParseError('Path {!r} does not match Template: {}'.format(path, self))

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
        for match in constants.MATCH_PATTERN.finditer(self._path):
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
            self._pattern += self._path[last_idx:start] + relative_template.pattern
            last_idx = end

        # Add any remaining path
        self._pattern += self._path[last_idx:]
        self._ordered_fields = tuple(ordered_fields)
