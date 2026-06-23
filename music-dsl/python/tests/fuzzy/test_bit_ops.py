from hypothesis import given
from hypothesis import strategies as st

from music_dsl.helpers import MAX_SUPPORTED, MIN_SUPPORTED, strip_left, strip_right


@given(
    bits=st.integers(min_value=MIN_SUPPORTED, max_value=MAX_SUPPORTED),
    x=st.integers(min_value=1, max_value=36),
)
def test_fuzz_strip_left(bits, x):
    bits_length = int.bit_length(bits)
    left_set_bit_shift_size = bits_length - x - 1
    if (
        x <= bits_length
        and left_set_bit_shift_size >= 0
        and bits & (1 << left_set_bit_shift_size)
    ):
        assert strip_left(bits=bits, x=x) == int(bin(bits)[2 + x :] or "0", 2)


@given(
    bits=st.integers(min_value=MIN_SUPPORTED, max_value=MAX_SUPPORTED),
    x=st.integers(min_value=0, max_value=36),
)
def test_fuzz_strip_right(bits, x):
    if x == int.bit_length(bits):
        assert strip_right(bits=bits, x=x) == 0
    if x < int.bit_length(bits):
        expected = int(bin(bits)[:-x] if x != 0 else bin(bits) or "0", 2)
        assert strip_right(bits=bits, x=x) == expected
