from tonalis.lint import lint
from tonalis.parser import parse_dsl


def _codes(s):
    r = parse_dsl(s)
    extra = lint(r.chart) if r.chart else []
    return {f.code for f in r.findings + extra}


def test_clean_chart_has_no_errors():
    r = parse_dsl("title:T\nkey:C\ntime:4/4\n[A]\n| C6 | A-7 | D7 | G7 |\n")
    assert not [f for f in lint(r.chart) if f.severity == "error"]


def test_beat_sum_error():
    # middle bar 2+1 = 3 != 4 (first/last are pickup-relaxed, so pad with clean bars)
    s = "title:T\nkey:C\ntime:4/4\n[A]\n| C6 | C6:2 D7:1 | C6 |\n"
    assert "beat-sum" in _codes(s)


def test_even_split_must_divide():
    s = "title:T\nkey:C\ntime:4/4\n[A]\n| C6 | C6 D7 E7 | C6 |\n"  # 3 chords in 4/4 (middle)
    assert "beat-sum" in _codes(s)


def test_bad_chord_error():
    assert "bad-chord" in _codes("title:T\nkey:C\ntime:4/4\n[A]\n| Cgarbage |\n")


def test_unbalanced_repeat_error():
    assert "unbalanced-repeat" in _codes(
        "title:T\nkey:C\ntime:4/4\n[A]\n{ | C6 | A-7 |\n"
    )


def test_too_many_codas_error():
    s = "title:T\nkey:C\ntime:4/4\n[A]\n@coda\n| C6 |\n@coda\n| D7 |\n@coda\n| E7 |\n"
    assert "coda-count" in _codes(s)


def test_coda_needs_segno_warning():
    s = "title:T\nkey:C\ntime:4/4\n[A]\n@coda\n| C6 |\n@coda\n| D7 |\n"
    r = parse_dsl(s)
    assert any(f.code == "coda-needs-segno" for f in lint(r.chart))


def test_allowed_uneven_beats_no_warning():
    s = "title:T\nkey:C\ntime:4/4\n[A]\n| C6 | C6:2 D7:1 E7:1 | C6 |\n"  # 2+1+1 allowed
    assert "beat-unsupported" not in _codes(s) and "beat-sum" not in _codes(s)
