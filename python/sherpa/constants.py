import re

REF_NAMETEMPLATE = '#'
REF_PATHTEMPLATE = '@'
MATCH_PATTERN = re.compile('{([%s%s])?(\w+)}' % (REF_PATHTEMPLATE, REF_NAMETEMPLATE))

KEY_NAMETEMPLATE = 'names'
KEY_PATHTEMPLATE = 'paths'
KEY_TOKEN = 'tokens'
TOKEN_TYPE = 'type'

WILDCARD = '*'
WILDCARD_ONE = '?'
NUMBER_PATTERN = '0-9'
STRING_BLACKLIST = '/._'
