class TemplateResolverError(Exception):
    """ Generic base exception for all TemplateResolver errors """


class FormatError(TemplateResolverError):
    """ Failure to format a value """


class ParseError(TemplateResolverError):
    """ Failure to parse a value """
