from collections import namedtuple
from dataclasses import dataclass
from enum import Enum
from functools import cache, reduce
from typing import List

from music_dsl.domain.static import Extensions, Notes, Seventh, Triad
from music_dsl.helpers import strip_left, strip_right

EMPTY_CHORD_ENCODING = int("1000000000000000000", 2)
CHORD_ENCODING_BIT_LENGTH = int.bit_length(EMPTY_CHORD_ENCODING)
DIMINISHED_ENCODING = int("1001001001000000000", 2)

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
    """A chord's interval content packed into a CHORD_ENCODING_BIT_LENGTH-bit vector.

    The bit layout lets diatonicity be checked with a single bitwise AND against a
    scale mask (see ``scan_scale`` / ``transactions.is_diatonic``).
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


def _scale_mask(*pitch_classes: int) -> int:
    """Build a scale's 36-bit mask from its pitch classes (semitones above the
    tonic, 0-11). The 12-bit pattern (MSB = tonic) is repeated 3x so the modal
    scan can rotate to any root. Reproduces the hand-written masks exactly."""
    pattern = 0
    for pc in pitch_classes:
        pattern |= 1 << (11 - pc)
    return (pattern << 24) | (pattern << 12) | pattern


@dataclass(frozen=True)
class ScaleDescriptor:
    """Everything the library needs to know about a scale.

    ``mask`` is the 12-bit pitch-class set repeated 3x (36 bits). The triple copy
    lets the sliding-window scan in ``scan_scale``/``is_diatonic`` rotate the scale
    to any mode/root without the window falling off the most-significant end.

    ``supports_diatonic_function`` drives the two-tier model: membership
    (``contains``) is defined for every scale, but functional queries
    (``is_diatonic`` / harmonic function) are only meaningful where a tonal
    hierarchy exists. Symmetric/atonal scales set this False and those queries
    refuse rather than return an answer that looks authoritative but isn't.
    """

    mask: int
    name: str
    category: str
    supports_diatonic_function: bool


class NonFunctionalScaleError(ValueError):
    """A functional query (diatonicity / harmonic function) was made against a
    scale with no meaningful tonal-function model (e.g. whole-tone, diminished,
    augmented, chromatic). Membership via ``contains`` still works for these."""


def _fn(mask: int, name: str, category: str) -> ScaleDescriptor:
    """A functional scale (has a tonal hierarchy; diatonic queries are defined)."""
    return ScaleDescriptor(mask, name, category, True)


def _sym(mask: int, name: str, category: str) -> ScaleDescriptor:
    """A symmetric/atonal scale (no tonal-function model; membership only)."""
    return ScaleDescriptor(mask, name, category, False)


class Scales(Enum):
    # --- Modes of the major scale (functional) --------------------------------
    Major = _fn(_scale_mask(0, 2, 4, 5, 7, 9, 11), "Major (Ionian)", "major-mode")
    Dorian = _fn(_scale_mask(0, 2, 3, 5, 7, 9, 10), "Dorian", "major-mode")
    Phrygian = _fn(_scale_mask(0, 1, 3, 5, 7, 8, 10), "Phrygian", "major-mode")
    Lydian = _fn(_scale_mask(0, 2, 4, 6, 7, 9, 11), "Lydian", "major-mode")
    Mixolydian = _fn(_scale_mask(0, 2, 4, 5, 7, 9, 10), "Mixolydian", "major-mode")
    Minor = _fn(_scale_mask(0, 2, 3, 5, 7, 8, 10), "Natural minor (Aeolian)", "major-mode")
    Locrian = _fn(_scale_mask(0, 1, 3, 5, 6, 8, 10), "Locrian", "major-mode")

    # --- Melodic minor and its modes (functional) -----------------------------
    MelodicMinor = _fn(_scale_mask(0, 2, 3, 5, 7, 9, 11), "Melodic minor", "melodic-minor")
    DorianFlat2 = _fn(_scale_mask(0, 1, 3, 5, 7, 9, 10), "Dorian b2", "melodic-minor")
    LydianAugmented = _fn(_scale_mask(0, 2, 4, 6, 8, 9, 11), "Lydian augmented", "melodic-minor")
    LydianDominant = _fn(_scale_mask(0, 2, 4, 6, 7, 9, 10), "Lydian dominant", "melodic-minor")
    MixolydianFlat6 = _fn(_scale_mask(0, 2, 4, 5, 7, 8, 10), "Mixolydian b6", "melodic-minor")
    LocrianNatural2 = _fn(_scale_mask(0, 2, 3, 5, 6, 8, 10), "Locrian natural 2", "melodic-minor")
    Altered = _fn(_scale_mask(0, 1, 3, 4, 6, 8, 10), "Altered (Super Locrian)", "melodic-minor")

    # --- Harmonic minor and its modes (functional) ----------------------------
    HarmonicMinor = _fn(_scale_mask(0, 2, 3, 5, 7, 8, 11), "Harmonic minor", "harmonic-minor")
    LocrianNatural6 = _fn(_scale_mask(0, 1, 3, 5, 6, 9, 10), "Locrian natural 6", "harmonic-minor")
    IonianSharp5 = _fn(_scale_mask(0, 2, 4, 5, 8, 9, 11), "Ionian #5", "harmonic-minor")
    DorianSharp4 = _fn(_scale_mask(0, 2, 3, 6, 7, 9, 10), "Dorian #4 (Ukrainian)", "harmonic-minor")
    PhrygianDominant = _fn(_scale_mask(0, 1, 4, 5, 7, 8, 10), "Phrygian dominant", "harmonic-minor")
    LydianSharp2 = _fn(_scale_mask(0, 3, 4, 6, 7, 9, 11), "Lydian #2", "harmonic-minor")
    Ultralocrian = _fn(_scale_mask(0, 1, 3, 4, 6, 8, 9), "Ultralocrian", "harmonic-minor")

    # --- Harmonic major and other named heptatonics (functional) --------------
    HarmonicMajor = _fn(_scale_mask(0, 2, 4, 5, 7, 8, 11), "Harmonic major", "harmonic-major")
    DoubleHarmonic = _fn(_scale_mask(0, 1, 4, 5, 7, 8, 11), "Double harmonic (Byzantine)", "exotic")
    HungarianMinor = _fn(_scale_mask(0, 2, 3, 6, 7, 8, 11), "Hungarian minor", "exotic")
    HungarianMajor = _fn(_scale_mask(0, 3, 4, 6, 7, 9, 10), "Hungarian major", "exotic")
    NeapolitanMajor = _fn(_scale_mask(0, 1, 3, 5, 7, 9, 11), "Neapolitan major", "exotic")
    NeapolitanMinor = _fn(_scale_mask(0, 1, 3, 5, 7, 8, 11), "Neapolitan minor", "exotic")

    # --- Pentatonic and blues (functional) ------------------------------------
    MajorPentatonic = _fn(_scale_mask(0, 2, 4, 7, 9), "Major pentatonic", "pentatonic")
    MinorPentatonic = _fn(_scale_mask(0, 3, 5, 7, 10), "Minor pentatonic", "pentatonic")
    Blues = _fn(_scale_mask(0, 3, 5, 6, 7, 10), "Blues (minor)", "blues")

    # --- Bebop (functional, 8-note; passing tone documented in SPEC) -----------
    BebopDominant = _fn(_scale_mask(0, 2, 4, 5, 7, 9, 10, 11), "Bebop dominant", "bebop")
    BebopMajor = _fn(_scale_mask(0, 2, 4, 5, 7, 8, 9, 11), "Bebop major", "bebop")
    BebopDorian = _fn(_scale_mask(0, 2, 3, 4, 5, 7, 9, 10), "Bebop Dorian", "bebop")
    BebopMinor = _fn(_scale_mask(0, 2, 3, 5, 7, 9, 10, 11), "Bebop minor", "bebop")

    # --- Symmetric / atonal (NON-functional: membership only) -----------------
    WholeTone = _sym(_scale_mask(0, 2, 4, 6, 8, 10), "Whole tone", "symmetric")
    DiminishedHalfWhole = _sym(
        _scale_mask(0, 1, 3, 4, 6, 7, 9, 10), "Diminished (half-whole)", "symmetric"
    )
    DiminishedWholeHalf = _sym(
        _scale_mask(0, 2, 3, 5, 6, 8, 9, 11), "Diminished (whole-half)", "symmetric"
    )
    Augmented = _sym(_scale_mask(0, 3, 4, 7, 8, 11), "Augmented", "symmetric")
    Chromatic = _sym(_scale_mask(*range(12)), "Chromatic", "atonal")


def contains(scale: "Scales", pitch_class: int) -> bool:
    """True if ``pitch_class`` (0-11 semitones above the tonic) is in the scale.

    Defined for EVERY scale — the membership tier of the two-tier model — including
    symmetric/atonal scales whose functional queries are undefined.
    """
    mask = scale.value.mask
    size = mask.bit_length() // 3
    pattern = mask >> (2 * size)  # the leading 12-bit copy
    return bool(pattern >> (size - 1 - (pitch_class % size)) & 1)


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
