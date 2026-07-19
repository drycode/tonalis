import json

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
from tonalis.ast import Cell
from tonalis import parse_dsl, to_json

def test_chord_obj_returns_chord_for_present_token():
    assert isinstance(Cell("C^7").chord_obj, Chord)

def test_chord_obj_none_for_empty_and_no_chord_and_slash():
    assert Cell("").chord_obj is None
    assert Cell("N.C.").chord_obj is None
    assert Cell("/A").chord_obj is None

def test_chord_obj_raises_on_malformed_present():
    try:
        Cell("xyzzy").chord_obj
        assert False, "expected raise"
    except InvalidChordStringException:
        pass

def test_chord_obj_or_none_never_raises():
    assert Cell("xyzzy").chord_obj_or_none is None
    assert isinstance(Cell("C^7").chord_obj_or_none, Chord)

def test_chord_obj_never_serialized():
    res = parse_dsl("title: T\nkey: C\ntime: 4/4\n[A]\n| C^7 | A-7 |\n")
    blob = to_json(res.chart)
    assert "chord_obj" not in blob
