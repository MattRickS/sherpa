class PathResolverError(Exception):
    """ Generic base exception for all PathResolver errors """


class FormatError(PathResolverError):
    """ Failure to format a value """


class ParseError(PathResolverError):
    """ Failure to parse a value """
