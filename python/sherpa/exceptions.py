class TemplateResolverError(Exception):
    """ Generic base exception for all TemplateResolver errors """


class FormatError(TemplateResolverError):
    """ Failure to format a value """


class ParseError(TemplateResolverError):
    """ Failure to parse a value """


class MissingTemplateError(TemplateResolverError):
    """ Error with a missing template of any type """


class MissingTokenError(TemplateResolverError):
    """ Error with a missing token """
