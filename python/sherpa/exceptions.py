class TemplateResolverError(Exception):
    """ Generic base exception for all TemplateResolver errors """


class FormatError(TemplateResolverError):
    """ Failure to format a value """


class ParseError(TemplateResolverError):
    """ Failure to parse a value """


class ConfigError(TemplateResolverError):
    """ Any errors raised from reading a template/token configuration """


class MissingTemplateError(ConfigError):
    """ Error with a missing template of any type """


class MissingTokenError(ConfigError):
    """ Error with a missing token """


class TokenConfigError(ConfigError):
    """ Error with a configuration value for a token """


class TemplateValidationError(ConfigError):
    """ Errors with template validation """
