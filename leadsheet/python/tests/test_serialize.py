"""Round-trip tests for the canonical AST JSON serializer (Task 1.1).

The serializer is the contract that makes ``expect.ast`` in a conformance case
language-agnostic. The core property is ``ast_from_json(ast_to_json(c)) == c`` and
that the emitted dict is plain-JSON-serializable with stable key order.
"""

import json
from pathlib import Path

import pytest

from tonalis.ast import Barline, Cell, LeadSheet, Measure, Section, SectionKind
from tonalis.parser import parse_dsl
from tonalis.serialize import ast_from_json, ast_to_json

FIX = Path(__file__).parent / "fixtures"
GOLDENS = sorted(FIX.glob("*.dsl"))


def _roundtrip(chart: LeadSheet):
    d = ast_to_json(chart)
    # must be plain-JSON-serializable (no tuples/dataclasses leaking through)
    s = json.dumps(d)
    d2 = json.loads(s)
    back = ast_from_json(d2)
    return d, back


@pytest.mark.parametrize("path", GOLDENS, ids=[p.stem for p in GOLDENS])
def test_golden_ast_roundtrips(path):
    chart = parse_dsl(path.read_text(encoding="utf-8")).chart
    assert chart is not None
    _, back = _roundtrip(chart)
    assert back == chart


def test_roundtrip_beats_alt_nav_case():
    # explicit :N beats, an inline alt, a time-change nav, segno + text nav, and an ending.
    dsl = (
        "title: T\ncomposer: C\nstyle: Swing\nkey: F\ntime: 4/4\n"
        "[A]\n@segno\n<verse>\n"
        "{ | C:2 G7:2 | D-7 G7(Db7) |1. C^7 } |2. F6 |\n"
        "[time: 3/4]\n| Bb6 |\n"
    )
    chart = parse_dsl(dsl).chart
    assert chart is not None
    d, back = _roundtrip(chart)
    assert back == chart
    # time nav is a [\"time\", [3, 4]] nested array in JSON, not a tuple-string
    navs = [m.nav for s in chart.sections for m in s.measures]
    json_navs = [m["nav"] for s in d["sections"] for m in s["measures"]]
    assert any(["time", [3, 4]] in nv for nv in json_navs)
    # meta time is a list in JSON, a tuple after round-trip
    assert d["meta"]["time"] == [4, 4]
    assert back.meta["time"] == (4, 4)
    # explicit beats survive
    first_cells = chart.sections[0].measures[0].cells
    assert [c.beats for c in first_cells] == [2, 2]
    assert [c.beats for c in back.sections[0].measures[0].cells] == [2, 2]
    # inline alt survives
    assert any(c.alt == "(Db7)" for s in back.sections for m in s.measures for c in m.cells)


def test_stable_key_order():
    chart = LeadSheet(
        meta={"title": "T", "key": "C", "time": (4, 4)},
        sections=[
            Section(
                label="A",
                kind=SectionKind.A,
                measures=[
                    Measure(
                        cells=[Cell(chord="C^7", beats=None, alt=None)],
                        ending=None,
                        bar_open=False,
                        barline=Barline.FINAL,
                        nav=(("segno",),),
                        line=7,
                    )
                ],
            )
        ],
    )
    d = ast_to_json(chart)
    assert d["schema_version"] == 1
    assert list(d.keys()) == ["schema_version", "meta", "sections"]
    assert list(d["sections"][0].keys()) == ["label", "kind", "measures"]
    assert list(d["sections"][0]["measures"][0].keys()) == [
        "cells",
        "ending",
        "bar_open",
        "barline",
        "nav",
        "hints",
        "line",
    ]
    assert list(d["sections"][0]["measures"][0]["cells"][0].keys()) == [
        "chord",
        "beats",
        "alt",
    ]
    assert ast_from_json(d) == chart


def test_from_json_rejects_unknown_major_version():
    import pytest

    from tonalis.serialize import ast_from_json

    with pytest.raises(ValueError):
        ast_from_json({"schema_version": 999, "meta": {}, "sections": []})


# --- cross-impl rejection contract (the canonical JSON is a public interface; the Py/TS/Rust ports
# must reject the SAME malformed inputs the SAME way: a clean ValueError/Error, never a TypeError
# crash / panic / silent coercion). Mirrors the TS `ast.from_json.test.ts` + Rust `unit.rs`. -------

def test_from_json_rejects_unknown_section_kind():
    # `{kind:"bridge"}` is not a neutral SectionKind -> reject, NOT coerce to *A.
    with pytest.raises(ValueError):
        ast_from_json({
            "schema_version": 1, "meta": {},
            "sections": [{"label": "X", "kind": "bridge", "measures": []}],
        })


def test_from_json_rejects_unknown_barline():
    # `{barline:"double"}` is not a neutral Barline -> reject, NOT coerce to normal.
    with pytest.raises(ValueError):
        ast_from_json({
            "schema_version": 1, "meta": {},
            "sections": [{
                "label": "A", "kind": "a",
                "measures": [{
                    "cells": [{"chord": "C", "beats": None, "alt": None}],
                    "ending": None, "bar_open": False, "barline": "double",
                    "nav": [], "hints": [], "line": 0,
                }],
            }],
        })


def test_from_json_rejects_string_and_null_schema_version_cleanly():
    # A string "2" and a null must BOTH raise a clean ValueError (NOT a TypeError on int(None),
    # NOT silently accepted as v1). Missing -> default 1 (accepted).
    for bad in ("2", None, "1", True):
        with pytest.raises(ValueError):
            ast_from_json({"schema_version": bad, "meta": {}, "sections": []})
    # missing schema_version defaults to 1 (accepted, no raise)
    assert ast_from_json({"meta": {}, "sections": []}) is not None
    # and the cleanliness: a null does NOT raise a TypeError
    try:
        ast_from_json({"schema_version": None, "meta": {}, "sections": []})
    except ValueError:
        pass
    except TypeError as e:  # pragma: no cover - this is the bug we fixed
        raise AssertionError(f"null schema_version raised TypeError, not ValueError: {e}")
