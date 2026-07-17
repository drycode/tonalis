import logging
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
logger = logging.getLogger(__name__)


def m_or_M_scaledegree(root: ScaleDegree, triad) -> ScaleDegree:
    # Major-third triads (major, augmented) and sus4 keep the major scale degree;
    # everything else (minor, dim, half-dim) lowers it.
    if triad and triad not in (Triad.Major, Triad.Augmented, Triad.Sus4):
        return root.to_minor()
    return root


def validate_attr_inputs(_7th, extensions):
    if not isinstance(extensions, Iterable):
        raise ValueError("Extensions is not iterable")

    # Added tensions (6/9/11/13) alongside a 7th are legitimate jazz voicings
    # (e.g. C13, C^9). They are encoded as plain interval bits, so we no longer
    # reject them here; doing so previously turned parseable chords into crashes.


@cache
def semitones_apart_ascending(root: Notes, note: Notes) -> int:
    try:
        return (get_index(note) + 12 - get_index(root)) % 12
    except TypeError as exc:
        logger.exception(
            f"Incorrect values passed to semitones_apart_ascending(root={root}, note={note})"
        )
        raise exc


@cache
def get_index(note: Union[Notes, ScaleDegree]) -> int:
    if isinstance(note, Notes):
        return TWELVE_TONES.index(note)
    elif isinstance(note, ScaleDegree):
        return SCALE_DEGREES.index(note.to_major())
    else:
        raise TypeError(f"Invalid type {type(note)} passed to get_index")


def strip_left(bits: int, x: int):
    """
    Remove x bits from left of bit array
    """
    if x == 0:
        return bits
    if MIN_SUPPORTED <= bits <= MAX_SUPPORTED:
        bit_length = int.bit_length(bits)
        if bit_length < x:
            raise ValueError("Attempting an invalid shift")
        mask = (1 << bit_length - x) - 1
        result = bits & mask
        if int.bit_length(result) != bit_length - x:
            raise ValueError(
                "Stripping left will reduce the fidelity of the bit array, because of leading zeros after the strip"
            )
        return result
    raise Exception("Unexpected behavior")


def strip_right(bits: int, x: int):
    """
    Remove x bits from right of bit array
    """
    if x > int.bit_length(bits):
        raise ValueError("Attempting an invalid shift")
    return bits >> x
