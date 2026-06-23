"""
SCRUBBED format supported chords can be found here https://www.irealpro.com/ireal-pro-file-format
"""

from enum import auto
from music_dsl.utils import JsonSerializableEnum


class HarmonicFunctions(JsonSerializableEnum):
    Dominant = auto()
    Subdominant = auto()
    Tonic = auto()


class Triad(JsonSerializableEnum):
    Major = ""
    Minor = "-"
    HalfDiminished = "h"
    Diminished = "o"
    Augmented = "+"
    Sus = "sus"
    Sus2 = "sus2"
    Sus4 = "sus4"


class Seventh(JsonSerializableEnum):
    Major = "^7"
    Minor = "7"
    _None = ""


class Extensions(JsonSerializableEnum):
    _None = ""
    add2 = "2"  # added 2nd (major 2nd, 2 semitones)
    add3 = "3"  # added/explicit 3rd (major 3rd, 4 semitones)
    b5 = "b5"
    add5 = "5"  # explicit 5th (power-chord style, perfect 5th)
    s5 = "#5"
    b6 = "b6"  # minor 6th; enharmonic with #5 (8 semitones)
    add6 = "6"
    b9 = "b9"
    add9 = "9"
    s9 = "#9"
    add11 = "11"
    s11 = "#11"
    b13 = "b13"
    add13 = "13"
    alt = "alt"  # altered dominant tensions (b9/#9/#11/b13)


SupportedExtensions = [
    Extensions.b5,
    Extensions.s5,
    Extensions.b13,
    Extensions.b9,
    Extensions._None,
    Extensions.s9,
    Extensions.s11,
    Extensions.b13,
]
