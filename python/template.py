"""
Goals:
* parse
* format
* relative templates
    root: "/root"
    relative: "/temp"
    path: "@root/folder/@relative"
* can have a path set as root which all resolved paths are joined to. This is
  done by a keyword to format which if not given, defaults to the set value, but
  can be explicitly set to something else or to None which enforces no root, eg:
    Pathresolver.set_root("/projects")
    template.format() --> "/projects/..."
* token options:
    default:
    type:
    choices: <-- introduces complications for searching (glob each, or glob wildcard and validate)
"""

WILDCARD = '*'


class Token(object):
    # Properties
    default = None       # default value (if any)
    name = None
    type = None          # type
    valid_values = None  # list

    # Methods
    def format(self):
        """converts it's data type to a formatted string"""
    def parse(self):
        """converts a string type to it's data type"""


class Template(object):
    # Properties
    parent = None    # The parent Template (if any)
    pattern = None   # The full path pattern
    relative = None  # The relative Template (if any)
    tokens = None    # dict[str, Token]

    # Methods
    def format(self, fields):
        """converts dict of fields to path"""
    def parse(self, path):
        """converts path to dic tof fields"""
    def paths(self, fields):
        """returns all paths using keys and wildcards/default for missing"""


class PathResolver(object):
    # Properties
    templates = None  # dict[str, Template]  # Also __getitem__

    # Methods
    def paths_from_template(self, template, fields):  # Template/str, dict
        """ same as Template.paths """
    def template_from_path(self, path, closest=False):
        """ extracts the Template that matches the path """

