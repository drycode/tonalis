"""DSL abstract syntax — frozen-ish dataclasses produced by the parser, consumed by the
linter and the iReal codec.

Phase 2: the IR is NEUTRAL. The root is ``LeadSheet`` (was ``DslChart``); a section carries a
neutral ``kind`` enum (was the iReal ``marker`` string); a measure carries a ``barline`` enum
(was the raw ``bar_close`` glyph) plus an opaque ``hints`` list (where ``@break`` lives — it has
no lead-sheet semantics). No field stores an iReal-ism; the codec maps kind/barline/hints to
``*A``/``Z``/``}``/``Y`` itself.
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


@dataclass
class Measure:
    cells: List[Cell] = field(default_factory=list)
    ending: Optional[int] = None  # 1./2. nth-ending number
    bar_open: bool = False  # preceded by '{'
    barline: Barline = Barline.NORMAL  # neutral right-barline (was bar_close: str)
    nav: Tuple = ()  # ('segno',), ('coda',), ('fine',), ('text', '<...>'), ('time', (n, d))
    hints: Tuple[str, ...] = ()  # opaque iReal render-hints, e.g. ('break',); NO semantics
    line: int = 0  # source line for findings


@dataclass
class Section:
    label: str
    kind: SectionKind  # neutral role (was the iReal marker string)
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
