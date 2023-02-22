from enum import Enum, auto


class HarmonicFunctions(Enum):
    Dominant = auto()
    Subdominant = auto()
    Tonic = auto()


class Triad(Enum):
    Major = ""
    Minor = "-"
    HalfDiminished = "h"
    Diminished = "o"
    Sus = "sus"
    Sus2 = "sus2"
    Sus4 = "sus4"


class Seventh(Enum):
    Major = "^7"
    Minor = "7"
    _None = ""


class Extensions(Enum):
    _None = ""
    b5 = "b5"
    s5 = "#5"
    add6 = "6"
    b9 = "b9"
    add9 = "9"
    s9 = "#9"
    add11 = "11"
    s11 = "#11"
    b13 = "b13"
    add13 = "13"


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
