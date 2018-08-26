from pathresolver.token import StringToken, IntToken
from pathresolver.exceptions import FormatError, ParseError


def test_int():
    cfg_int = """
    tokens:
        int1: int
        int2:
            type: int
            default: 2
        int3:
            type: int
            choices: [1, 2, 3, 4]
        int4:
            type: int
            choices: [1, 2, 3, 4]
            default: 4
        int5:
            type: int
            choices: [1, 2, 3, 4]
            default: 5
    """

    itoken = IntToken('int', padding=3)
    assert itoken.format(1) == '001'
    assert itoken.parse('001') == 1

    # Invalid padding
    try:
        itoken.parse('1')
        assert False
    except ParseError:
        pass

    itoken = IntToken('int', valid_values=['1', '2', '3'])
    assert itoken.parse('3') == 3
    try:
        itoken.parse('4')
        assert False
    except ParseError:
        pass

    itoken = IntToken('int', default='2', valid_values=['1', '2', '3'])

    try:
        itoken = IntToken('int', default='0', valid_values=['1', '2', '3'])
        assert False
    except ValueError:
        pass


if __name__ == '__main__':
    test_int()
