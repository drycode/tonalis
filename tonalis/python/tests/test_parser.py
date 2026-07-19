from tonalis.ast import Barline, SectionKind
from tonalis.parser import parse_dsl

HEADER = "title: A Train\ncomposer: Strayhorn\nkey: C\ntime: 4/4\n\n[A]\n| C6 | A-7 |\n"


def _chart(s):
    return parse_dsl(s).chart


def _errors(s):
    return {f.code for f in parse_dsl(s).findings if f.severity == "error"}


# --- T4: header / encoding / limits ---


def test_parses_header_and_meta():
    r = parse_dsl(HEADER)
    assert not [f for f in r.findings if f.severity == "error"]
    assert r.chart.meta["title"] == "A Train"
    assert r.chart.meta["key"] == "C"
    assert r.chart.meta["time"] == (4, 4)


def test_missing_required_header_is_error():
    assert "missing-header" in _errors("composer: x\n[A]\n| C6 |\n")


def test_empty_input_is_error():
    assert "empty-chart" in _errors("")


def test_bom_and_crlf_normalized():
    r = parse_dsl("﻿title: T\r\nkey: C\r\ntime: 4/4\r\n[A]\r\n| C6 |\r\n")
    assert r.chart.meta["title"] == "T"


def test_header_value_to_eol_no_inline_comment():
    assert (
        _chart("title: Blues #1\nkey: C\ntime: 4/4\n[A]\n| C6 |\n").meta["title"]
        == "Blues #1"
    )


def test_equals_in_metadata_is_error():
    assert "meta-delimiter" in _errors("title: A=B\nkey: C\ntime: 4/4\n[A]\n| C6 |\n")


def test_oversize_input_is_finding_not_crash():
    big = "title: T\nkey: C\ntime: 4/4\n[A]\n" + "| C6 |\n" * 100000
    assert "too-big" in _errors(big)


# --- T5: sections / measures / beats / alt / nav ---


def test_sections_and_measures():
    c = _chart("title: T\nkey: C\ntime: 4/4\n[A]\n| C6 | A-7 D7 | G7 |\n")
    assert c.sections[0].kind == SectionKind.A
    bars = c.sections[0].measures
    assert [[cell.chord for cell in m.cells] for m in bars] == [
        ["C6"],
        ["A-7", "D7"],
        ["G7"],
    ]


def test_explicit_beats():
    c = _chart("title: T\nkey: C\ntime: 4/4\n[A]\n| C6:2 D7:1 E7:1 |\n")
    cells = c.sections[0].measures[0].cells
    assert [(x.chord, x.beats) for x in cells] == [("C6", 2), ("D7", 1), ("E7", 1)]


def test_unknown_section_is_error():
    assert "unknown-section" in _errors(
        "title: T\nkey: C\ntime: 4/4\n[Bridge]\n| C6 |\n"
    )


def test_alt_chord_and_nochord():
    c = _chart("title: T\nkey: C\ntime: 4/4\n[A]\n| C6 (A-7 D7) | n |\n")
    assert c.sections[0].measures[0].cells[0].alt == "(A-7 D7)"
    assert c.sections[0].measures[1].cells[0].chord == "n"


def test_final_barline_z():
    c = _chart("title: T\nkey: C\ntime: 4/4\n[A]\n| C6 | A-7 | D7 | G7 Z\n")
    assert c.sections[0].measures[-1].barline == Barline.FINAL


# --- T6: repeats / endings / mid-tune time-sig ---


def test_repeat_and_split_endings():
    c = _chart("title: T\nkey: C\ntime: 4/4\n[A]\n{ | C-7 | F7 |1. C^7 } |2. A7 |\n")
    ms = c.sections[0].measures
    assert ms[0].bar_open is True
    assert any(m.ending == 1 for m in ms) and any(m.ending == 2 for m in ms)
    assert any(m.barline == Barline.REPEAT_END for m in ms)


def test_mid_tune_time_sig():
    c = _chart("title: T\nkey: C\ntime: 4/4\n[A]\n| C6 |\n[time: 3/4]\n| D-7 |\n")
    navs = [m.nav for m in c.sections[0].measures]
    assert any(("time", (3, 4)) in nav for nav in navs)


def test_segno_coda_nav():
    c = _chart("title: T\nkey: C\ntime: 4/4\n[A]\n@segno\n| C6 |\n@coda\n| D7 |\n")
    navs = [n for m in c.sections[0].measures for n in m.nav]
    assert ("segno",) in navs and ("coda",) in navs


# --- singleton / mutually-exclusive attribute guards ---


def _codes(s):
    return {(f.severity, f.code) for f in parse_dsl(s).findings}


def test_conflicting_singleton_header_is_error():
    # Two DIFFERENT values for a singleton header are mutually exclusive -> error (blocks compile).
    assert "conflicting-header" in _errors(
        "title:T\nkey:C\ntime:4/4\ntime:3/4\n[A]\n| C |\n"
    )
    assert "conflicting-header" in _errors(
        "title:T\nkey:C\nkey:F\ntime:4/4\n[A]\n| C |\n"
    )
    assert "conflicting-header" in _errors(
        "title:T\ntitle:U\nkey:C\ntime:4/4\n[A]\n| C |\n"
    )


def test_duplicate_singleton_header_is_warning_not_error():
    # Same value restated is redundant, not fatal -> warning only, still compiles.
    codes = _codes("title:T\nkey:C\ntime:4/4\ntime:4/4\n[A]\n| C |\n")
    assert ("warning", "duplicate-header") in codes
    assert not any(sev == "error" for sev, _ in codes)


def test_redundant_mid_chart_time_change_warns_genuine_does_not():
    # [time: 4/4] when already in 4/4 is a no-op duplicate -> warning.
    assert ("warning", "redundant-time") in _codes(
        "title:T\nkey:C\ntime:4/4\n[A]\n| C |\n[time: 4/4]\n| D-7 |\n"
    )
    # a genuine meter change does NOT warn.
    assert not any(
        c == "redundant-time"
        for _, c in _codes(
            "title:T\nkey:C\ntime:4/4\n[A]\n| C |\n[time: 3/4]\n| D-7 |\n"
        )
    )
