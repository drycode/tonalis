import pytest
from music_dsl.encode import strip_left
from tests.testdata.other_intentional import EXAMPLE_ENCODINGS


@pytest.mark.parametrize(["_input", "expected"], EXAMPLE_ENCODINGS)
def test_encoding(_input, expected):
    if expected:
        assert _input.encoding == expected
    assert _input.encoding


class StripInput:
    def __init__(self, bits: bytes, x):
        self.bits = int(bits, base=2)
        self.x = x


@pytest.mark.parametrize(
    ["_input", "expected"],
    ((StripInput(b"111111111000000011", 2), "1111111000000011"),),
)
def test_strip_left(_input, expected):
    assert strip_left(
        _input.bits,
        _input.x,
    ) == int(expected, base=2)


@pytest.mark.parametrize(
    "_input",
    (
        StripInput(b"1000000000011", 2),
        StripInput(b"100000000110011", 2),
        StripInput(b"1001000010001011", 2),
        StripInput(b"1001000010001011", 2),
        StripInput(
            b"101011010101101011010101101011010101",
            8,
        ),
    ),
)
def test_strip_left_raises(_input):
    with pytest.raises(Exception):
        strip_left(_input.bits, _input.x)
