"""Tests for the canonical DSL text printer (Phase 2 §1.1).

Two gates: (1) IR -> text -> IR identity over fixtures + crafted cases; (2) IR -> text golden
strings (a shared parser/printer bug passes identity alone, so the golden is mandatory).
"""

from pathlib import Path

import pytest

from tonalis.parser import parse_dsl
from tonalis.serialize_text import serialize

FIX = Path(__file__).parents[1] / "fixtures"
GOLDENS = sorted(FIX.glob("*.dsl"))


def _norm(chart):
    """Zero out the ``line`` source-position artifact so identity compares lead-sheet semantics.

    ``line`` is a source-line index, not part of the chart's identity; the canonical printer
    re-flows the layout (blank line before each section, one body line per section), so absolute
    line numbers shift while every semantic field (cells/kind/barline/nav/hints) is preserved.
    """
    if chart is not None:
        for s in chart.sections:
            for m in s.measures:
                m.line = 0
    return chart


@pytest.mark.parametrize("path", GOLDENS, ids=[p.stem for p in GOLDENS])
def test_text_roundtrip_identity(path):
    ir = parse_dsl(path.read_text(encoding="utf-8")).chart
    assert ir is not None
    text = serialize(ir)
    ir2 = parse_dsl(text).chart
    assert ir2 is not None
    assert _norm(ir2) == _norm(ir)


def test_break_hint_roundtrips():
    dsl = "title: T\nkey: C\ntime: 4/4\n[Intro]\n| D-7 | G7 |\n@break\n[A]\n| C6 | A-7 |\n"
    ir = parse_dsl(dsl).chart
    text = serialize(ir)
    assert "@break" in text
    assert _norm(parse_dsl(text).chart) == _norm(ir)


def test_fine_roundtrips():
    dsl = "title: T\nkey: C\ntime: 4/4\n[A]\n@fine\n| C6 |\n"
    ir = parse_dsl(dsl).chart
    text = serialize(ir)
    assert "@fine" in text
    assert _norm(parse_dsl(text).chart) == _norm(ir)


def test_golden_simple():
    dsl = "title: T\nkey: C\ntime: 4/4\n[A]\n| C6 | A-7 |\n"
    ir = parse_dsl(dsl).chart
    assert serialize(ir) == "title: T\nkey: C\ntime: 4/4\n\n[A]\n| C6 | A-7 |\n"


def test_golden_repeat_ending_final():
    dsl = "title: T\nkey: C\ntime: 4/4\n[A]\n{ | C^7 |1. A-7 } |2. F6 ||\n"
    ir = parse_dsl(dsl).chart
    out = serialize(ir)
    # round-trip must hold and the canonical glyphs must appear
    assert _norm(parse_dsl(out).chart) == _norm(ir)
    assert "{ " in out and "}" in out and "||" in out and "1." in out and "2." in out
