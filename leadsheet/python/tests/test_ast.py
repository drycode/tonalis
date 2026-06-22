from tonalis.ast import (
    Barline,
    Cell,
    LeadSheet,
    LintFinding,
    Measure,
    ParseResult,
    Section,
    SectionKind,
)


def test_dataclasses_construct():
    cell = Cell(chord="C6")
    m = Measure(cells=[cell], barline=Barline.NORMAL)
    s = Section(label="A", kind=SectionKind.A, measures=[m])
    chart = LeadSheet(meta={"title": "X", "key": "C", "time": (4, 4)}, sections=[s])
    assert chart.sections[0].measures[0].cells[0].chord == "C6"
    f = LintFinding(severity="error", line=3, code="bad-chord", message="x")
    assert ParseResult(chart=chart, findings=[f]).findings[0].code == "bad-chord"


def test_cell_beats_and_alt():
    c = Cell(chord="C6", beats=2, alt="(A-7 D7)")
    assert c.beats == 2 and c.alt == "(A-7 D7)"
