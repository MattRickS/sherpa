# Sherpa

-- _Shows you your path_

### Terminology
* path: filesystem path, may or may not exist
* template: defined pattern that uses tokens to represent a path
* tokens: a placeholder name for a value in a template, has configuration values
* fields: A dictionary of key value pairs, where each key is the name of a token and the value is a valid value for the token.

Define template for filesystem paths using a configuration of tokens. Tokens are defined in a template with brackets around the token name, eg, `{token_name}`. Existing paths can be parsed to extract the fields it uses, and the template can be formatted with a set of fields to provide paths. Templates can also be used with wildcards to retrieve all matching paths that exist on disk.

Templates can reference other templates, either as a parent (ie, the root for the path), or anywhere else in the path as a relative path. Reference templates are defined the same as a token but are preceded by an @ symbol, eg, `@{other_template_name}`

Tokens have a number of available configuration options:
* default: value to use when not supplied to the Template methods
* choices: Only acceptable values to use for the value
* type: Data type to treat the value as. Available options are [float, int, str].
* padding: int/float only -- for integers this uses zero padding to the given length, for floats this pads the trailing digits with 0s to meet the given length.

<aside class="warning">
Warning: Wildcard fields in Template.paths() will ignore hidden files/folders.
</aside>

### Further goals
* referenced templates with fixed tokens, eg, '@{task:storage=.archive}/v{version}'. This makes using separate storages with mirrored folder structures easy to manage.
