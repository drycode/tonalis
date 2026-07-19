"""DSL abstract syntax — frozen-ish dataclasses produced by the parser, consumed by the
linter and a downstream codec.

Phase 2: the IR is NEUTRAL. The root is ``LeadSheet`` (was ``DslChart``); a section carries a
neutral ``kind`` enum (derived by the parser from the bracket name); a measure carries a
``barline`` enum (was the raw ``bar_close`` glyph) plus an opaque ``hints`` list (where
``@break`` lives — it has no lead-sheet semantics). No field stores a format-specific value; a
downstream codec maps kind/barline/hints to the target format's section/barline markers itself.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class SectionKind(str, Enum):
    """Neutral section role, derived by the parser from the bracket name."""
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    INTRO = "intro"
    VERSE = "verse"


class Barline(str, Enum):
    """Neutral right-barline. ``'|'`` -> NORMAL, ``'}'`` -> REPEAT_END, ``'Z'``/``'||'`` -> FINAL."""
    NORMAL = "normal"
    REPEAT_END = "repeat_end"
    FINAL = "final"


@dataclass
class Cell:
    chord: str
    beats: Optional[int] = None  # explicit :N, else None (even split of the bar)
    alt: Optional[str] = None  # raw "(A-7 D7)" alt-chord text, if any

    @property
    def chord_obj(self):
        """Lazy MusicDSL Chord for a present chord token; None for empty / no-chord /
        bare-slash cells; raises InvalidChordStringException for a malformed-present token."""
        from music_dsl.domain.chords.chord import Chord  # lazy: keeps the dep at use-time
        t = (self.chord or "").replace("*", "")
        if not t or t in ("N.C.", "n") or t.startswith("/"):
            return None
        return Chord(t)

    @property
    def chord_obj_or_none(self):
        """Non-raising form of chord_obj (None for malformed tokens too)."""
        from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
        try:
            return self.chord_obj
        except InvalidChordStringException:
            return None


@dataclass
class Measure:
    cells: List[Cell] = field(default_factory=list)
    ending: Optional[int] = None  # 1./2. nth-ending number
    bar_open: bool = False  # preceded by '{'
    barline: Barline = Barline.NORMAL  # neutral right-barline (was bar_close: str)
    nav: Tuple = ()  # ('segno',), ('coda',), ('fine',), ('text', '<...>'), ('time', (n, d))
    hints: Tuple[str, ...] = ()  # opaque render-hints, e.g. ('break',); NO semantics
    line: int = 0  # source line for findings


@dataclass
class Section:
    label: str
    kind: SectionKind  # neutral role (the parser derives it from the bracket name)
    measures: List[Measure] = field(default_factory=list)


@dataclass
class LeadSheet:
    meta: dict = field(default_factory=dict)  # title/composer/style/key/time
    sections: List[Section] = field(default_factory=list)


@dataclass
class LintFinding:
    severity: str  # "error" | "warning"
    line: int
    code: str
    message: str


@dataclass
class ParseResult:
    chart: Optional[LeadSheet]
    findings: List[LintFinding] = field(default_factory=list)
