from functools import cache
from typing import Iterable, Union

from music_dsl.domain.static import (
    SCALE_DEGREES,
    TWELVE_TONES,
    Extensions,
    Notes,
    ScaleDegree,
    Seventh,
    Triad,
)

MIN_SUPPORTED = int("1000000000000", 2)
MAX_SUPPORTED = int("1111111111111" * 3, 2)


def m_or_M_scaledegree(root: ScaleDegree, triad) -> ScaleDegree:
    if triad and (triad != Triad.Major and triad != Triad.Sus4):
        return root.to_minor()
    return root


def validate_attr_inputs(_7th, extensions):
    if not isinstance(extensions, Iterable):
        raise Exception("Extensions is not iterable")

    if _7th != Seventh._None:
        if set(extensions) & set(
            [
                Extensions.add6,
                Extensions.add11,
                Extensions.add9,
                Extensions.add13,
            ]
        ):
            raise Exception(
                "We currently don't support 6,9,11,13 chords. Found {}",
                set(extensions)
                & set(
                    [
                        Extensions.add6,
                        Extensions.add11,
                        Extensions.add9,
                        Extensions.add13,
                    ]
                ),
            )


@cache
def semitones_apart(root: Notes, note: Notes) -> int:
    return (get_index(note) + 12 - get_index(root)) % 12


@cache
def get_index(note: Union[Notes, ScaleDegree]) -> int:
    if isinstance(note, Notes):
        return TWELVE_TONES.index(note)
    elif isinstance(note, ScaleDegree):
        return SCALE_DEGREES.index(note.to_major())
    else:
        raise TypeError(f"Invalid type {type(note)} passed to get_index")


########## Needs organization ###############
def strip_left(bits: int, x: int):
    """
    Remove x bits from left of bit array
    """
    if x == 0:
        return bits
    if MIN_SUPPORTED <= bits <= MAX_SUPPORTED:
        bit_length = int.bit_length(bits)
        if bit_length < x:
            raise Exception("Attempting an invalid shift")
        mask = (1 << bit_length - x) - 1
        result = bits & mask
        if int.bit_length(result) != bit_length - x:
            raise Exception(
                "Stripping left will reduce the fidelity of the bit array, because of leading zeros after the strip"
            )
        return result
    raise Exception("Unexpected behavior")


def strip_right(bits: int, x: int):
    """
    Remove x bits from right of bit array
    """
    if x > int.bit_length(bits):
        raise Exception("Attempting an invalid shift")
    return bits >> x


#############################################
