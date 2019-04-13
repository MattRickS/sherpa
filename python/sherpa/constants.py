import re

MATCH_PATTERN = re.compile('{(@)?(\w+)}')

ENV_VAR = 'PATHRESOLVER_CONFIG'

TEMPLATE_KEY = 'templates'
TOKEN_KEY = 'tokens'
TOKEN_TYPE = 'type'

WILDCARD = '*'
WILDCARD_ONE = '?'
