"""Canonical IR <-> JSON serialization for the conformance suite.

Phase 2: the JSON reflects the NEUTRAL IR and carries a top-level ``schema_version: 1``.
``ast_from_json`` rejects an unknown major version. ``LeadSheet`` replaces ``DslChart``;
``Section.kind`` replaces ``marker``; ``Measure.barline`` (enum) replaces ``bar_close`` (glyph);
``Measure.hints`` is a new opaque string list. ``nav`` round-trips list<->tuple as before; the
new ``fine`` nav item is a bare ``["fine"]``.
"""

from tonalis.ast import Barline, Cell, LeadSheet, Measure, Section, SectionKind

SCHEMA_VERSION = 1


def _meta_to_json(meta: dict) -> dict:
    out = {}
    for k, v in meta.items():
        if k == "time" and isinstance(v, tuple):
            out[k] = list(v)
        else:
            out[k] = v
    return out


def _meta_from_json(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if k == "time" and isinstance(v, list):
            out[k] = tuple(v)
        else:
            out[k] = v
    return out


def _nav_to_json(nav) -> list:
    return [_nav_item_to_json(item) for item in nav]


def _nav_item_to_json(item):
    return [_nav_atom_to_json(a) for a in item]


def _nav_atom_to_json(a):
    if isinstance(a, tuple):
        return list(a)
    return a


def _nav_from_json(nav) -> tuple:
    return tuple(_nav_item_from_json(item) for item in nav)


def _nav_item_from_json(item) -> tuple:
    return tuple(_nav_atom_from_json(a) for a in item)


def _nav_atom_from_json(a):
    if isinstance(a, list):
        return tuple(a)
    return a


def _cell_to_json(c: Cell) -> dict:
    return {"chord": c.chord, "beats": c.beats, "alt": c.alt}


def _cell_from_json(d: dict) -> Cell:
    return Cell(chord=d["chord"], beats=d.get("beats"), alt=d.get("alt"))


def _measure_to_json(m: Measure) -> dict:
    return {
        "cells": [_cell_to_json(c) for c in m.cells],
        "ending": m.ending,
        "bar_open": m.bar_open,
        "barline": m.barline.value,
        "nav": _nav_to_json(m.nav),
        "hints": list(m.hints),
        "line": m.line,
    }


def _measure_from_json(d: dict) -> Measure:
    return Measure(
        cells=[_cell_from_json(c) for c in d["cells"]],
        ending=d.get("ending"),
        bar_open=d.get("bar_open", False),
        barline=Barline(d.get("barline", "normal")),
        nav=_nav_from_json(d.get("nav", [])),
        hints=tuple(d.get("hints", [])),
        line=d.get("line", 0),
    )


def _section_to_json(s: Section) -> dict:
    return {
        "label": s.label,
        "kind": s.kind.value,
        "measures": [_measure_to_json(m) for m in s.measures],
    }


def _section_from_json(d: dict) -> Section:
    return Section(
        label=d["label"],
        kind=SectionKind(d["kind"]),
        measures=[_measure_from_json(m) for m in d["measures"]],
    )


def ast_to_json(chart: LeadSheet) -> dict:
    """Serialize a :class:`LeadSheet` to the canonical JSON-able dict (SPEC.md §2.1)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "meta": _meta_to_json(chart.meta),
        "sections": [_section_to_json(s) for s in chart.sections],
    }


# Public aliases (spec §1.1 surface names): to_json / from_json.
to_json = ast_to_json


def _check_schema_version(d: dict) -> None:
    """Reject an unknown/malformed ``schema_version`` with a clean ValueError.

    Missing -> default 1 (accepted). Present must be the INTEGER ``SCHEMA_VERSION`` — a string
    ``"2"``, ``null`` (Python ``None``), a bool, or any non-1 int are all rejected with a
    ValueError (never a TypeError crash on ``int(None)``). Consistent with the TS/Rust ports.
    """
    if "schema_version" not in d:
        return
    version = d["schema_version"]
    # bool is an int subclass but is never a valid version; reject it explicitly.
    if isinstance(version, bool) or not isinstance(version, int) or version != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema_version {version!r}; this build understands {SCHEMA_VERSION}"
        )


def ast_from_json(d: dict) -> LeadSheet:
    """Inverse of :func:`ast_to_json`. Rejects an unknown major schema version, an unknown
    ``Section.kind``, or an unknown ``Measure.barline`` with a clean ValueError (the canonical
    JSON is a public interface — malformed input is rejected uniformly across all three ports)."""
    _check_schema_version(d)
    return LeadSheet(
        meta=_meta_from_json(d.get("meta", {})),
        sections=[_section_from_json(s) for s in d.get("sections", [])],
    )


from_json = ast_from_json
