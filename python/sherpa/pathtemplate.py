import glob
import os

from sherpa import constants
from sherpa.template import Template
from sherpa.token import Token


class PathTemplate(Template):
    def __init__(self, name, config_string, parent=None, relatives=None, tokens=None):
        """
        :param str              name:
        :param str              config_string:
        :param Template         parent:
        :param list[Template]   relatives:
        :param dict[str, Token] tokens:
        """
        super(PathTemplate, self).__init__(name, config_string, relatives=relatives, tokens=tokens)
        self._parent = parent

    def __repr__(self):
        return 'PathTemplate({!r}, {!r}, parent={}, relatives={}, tokens={})'.format(
            self._name, self._config_string, self._parent, self._relatives, self._local_tokens
        )

    @property
    def linked_templates(self):
        """
        All immediate templates linked to this template, relatives and parent.

        :rtype: list[Template]
        """
        return ((self._parent, ) if self._parent else ()) + self._relatives

    @property
    def parent(self):
        """
        The leading referenced template if one exists

        :rtype: Template
        """
        return self._parent

    @property
    def relatives(self):
        """
        All immediate linked templates that are not the parent, ie, that do not
        define the root of the path

        :rtype: tuple[Template]
        """
        return self._relatives

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

    def join(self, template):
        """
        Appends the given template, returning a new PathTemplate object.
        Intended for combining relative templates on the fly.

        :param Template|str template: Suffix template or string
        :rtype: Template
        """
        path_template = super(PathTemplate, self).join(template)
        path_template._parent = self._parent
        return path_template

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

    def _parse(self, string, regex):
        string = string.replace(os.path.sep, '/')
        return super(PathTemplate, self)._parse(string, regex)
