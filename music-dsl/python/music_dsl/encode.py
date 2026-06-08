from enum import Enum
from functools import cache, reduce
from typing import List

from music_dsl.domain.static import Extensions, Notes, Seventh, Triad
from music_dsl.helpers import strip_left, strip_right

EMPTY_CHORD_ENCODING = int("1000000000000000000", 2)
CHORD_ENCODING_BIT_LENGTH = int.bit_length(EMPTY_CHORD_ENCODING)
DIMINISHED_ENCODING = int("1001001001000000000", 2)


from collections import namedtuple

Context = namedtuple("Context", "chord_root, contextual_tonic")

EncodingMap = {
    Triad.Major: [4, 7],
    Triad.Minor: [3, 7],
    Triad.Diminished: [3, 6],
    Triad.HalfDiminished: [3, 6],
    Triad.Augmented: [4, 8],
    Triad.Sus2: [2, 7],
    Triad.Sus: [5, 7],
    Triad.Sus4: [5, 7],
    Extensions.add2: [2],  # major 2nd
    Extensions.add3: [4],  # major 3rd
    Extensions.b5: [6],
    Extensions.add5: [7],  # perfect 5th
    Extensions.s5: [8],
    Extensions.b6: [8],  # minor 6th, enharmonic with #5
    Extensions.add6: [9],
    Seventh.Minor: [10],
    Seventh.Major: [11],
    Extensions.b9: [12],
    Extensions.add9: [13],
    Extensions.s9: [14],
    Extensions.add11: [15],
    Extensions.s11: [16],
    Extensions.b13: [17],
    Extensions.add13: [18],
    # An altered dominant carries the altered tensions b9/#9/#11/b13. This is a
    # minimal, sane interval set so `7alt` parses and encodes deterministically;
    # full chord-scale spelling is out of scope here.
    Extensions.alt: [12, 14, 16, 17],
    Seventh._None: [],
}


class Encoding:
    """
    TODO: Currently we're going to store the core and extensions in a
    CHORD_ENCODING_BIT_LENGTH array, but there's opportunity here to combine disparate
    pieces of the arrays using bit manipulation. this will allow us to compare smaller
    arrays against the Scale for Diatonicity as well, reducing time and space
    """

    def __init__(
        self,
        root: Notes,
        triad: Triad,
        _7th: Seventh,
        contextual_tonic: Notes = None,
        extensions: Extensions = None,
    ):
        self._core = (
            DIMINISHED_ENCODING
            if triad == Triad.Diminished
            else self._encode(EncodingMap[triad] + EncodingMap[_7th] or [])
        )
        self._extensions = self._encode(
            reduce(lambda x, y: x + EncodingMap.__getitem__(y), extensions, [])
        )
        self._context = Context(root, contextual_tonic)

    @property
    def value(self):
        return self._core | self._extensions

    @property
    def core(self):
        return self._core

    @property
    def extensions(self):
        return self._extensions

    @property
    def context(self):
        return self._context

    def _encode(self, bit_positions):
        if not bit_positions:
            return 0
        encoding = EMPTY_CHORD_ENCODING
        for shift in bit_positions:
            encoding |= 1 << CHORD_ENCODING_BIT_LENGTH - (shift + 1)
        return encoding


class Scales(Enum):
    Major = int("101011010101" * 3, 2)
    # Natural minor (Aeolian). Repeated 3x like Major so the modal-distance
    # scan in `is_diatonic`/`scan_scale` can align the scale to any root.
    Minor = int("101101011010" * 3, 2)
    # Harmonic minor: raised 7th gives the diatonic V7 of a minor key.
    HarmonicMinor = int("101101011001" * 3, 2)


@cache
def scan_scale(scale: int, chord: int) -> List[int]:
    """
    Returns a list of possible diatonic positions for a chord in a scale.
    And empty list signals non-diatonicity
    """
    scale_size = int.bit_length(scale) // 3
    chord_bits = strip_right(chord, 7)
    count = 0
    result = []
    for i in range(scale_size):
        scale_bits = strip_right(strip_left(scale, i), scale_size * 2 - i)
        if chord_bits & scale_bits == chord_bits:
            result.append(count)
        count += 1
    return result
