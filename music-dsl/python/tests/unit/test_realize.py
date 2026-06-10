"""Tests for pitch realization (music_dsl.realize)."""

import pytest

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.static import Intervals, Notes, ScaleDegree
from music_dsl.encode import Scales
from music_dsl.realize import (
    chord_pitches,
    interval_pitches,
    midi_to_hz,
    note_to_midi,
    scale_degree_pitch,
    scale_pitches,
)


def test_note_to_midi():
    assert note_to_midi(Notes.C, 4) == 60      # middle C
    assert note_to_midi(Notes.A, 4) == 69      # A440
    assert note_to_midi(Notes.C, 5) == 72
    assert note_to_midi(Notes.C, 3) == 48


def test_note_to_midi_is_enharmonic():
    assert note_to_midi(Notes("C#")) == note_to_midi(Notes("Db"))


def test_midi_to_hz():
    assert midi_to_hz(69) == pytest.approx(440.0)
    assert midi_to_hz(81) == pytest.approx(880.0)       # octave up
    assert midi_to_hz(60) == pytest.approx(261.6256, rel=1e-4)


def test_interval_pitches_accepts_int_or_interval():
    assert interval_pitches(Notes.C, 7) == [60, 67]              # perfect 5th
    assert interval_pitches(Notes.C, Intervals(4)) == [60, 64]   # major 3rd


@pytest.mark.parametrize("sym,expected", [
    ("C^7", [60, 64, 67, 71]),   # maj7
    ("C-7", [60, 63, 67, 70]),   # min7
    ("C7",  [60, 64, 67, 70]),   # dominant 7
    ("C+",  [60, 64, 68]),       # augmented triad (parser-fidelity grammar)
])
def test_chord_pitches(sym, expected):
    assert chord_pitches(Chord(sym)) == expected


def test_chord_pitches_respects_octave():
    assert chord_pitches(Chord("C^7"), octave=5) == [72, 76, 79, 83]


def test_scale_pitches_major():
    assert scale_pitches(Notes.C, Scales.Major) == [60, 62, 64, 65, 67, 69, 71, 72]


def test_scale_degree_pitch():
    assert scale_degree_pitch(ScaleDegree.I, Notes.C) == 60
    assert scale_degree_pitch(ScaleDegree.V, Notes.C) == 67
    assert scale_degree_pitch(ScaleDegree.I, Notes.G) == 67   # tonic of G


def test_o7_renders_diminished_seventh():
    assert chord_pitches(Chord("Co7"), 4) == [60, 63, 66, 69]


def test_h7_keeps_minor_seventh():
    assert chord_pitches(Chord("Ch7"), 4) == [60, 63, 66, 70]


def test_o7_distinct_from_h7():
    assert chord_pitches(Chord("Co7"), 4) != chord_pitches(Chord("Ch7"), 4)


from music_dsl.domain.chords.numeric_chord import NumericChord
from music_dsl.transactions import chord_in_key


def _ck(numeral, key):
    # Compare on the canonical Chord notation. Chord.__repr__ wraps the string
    # as "<Chord F7>"; _chord_str is the bare, round-trippable notation ("F7").
    return chord_in_key(NumericChord.from_chord_string(numeral), key)._chord_str


@pytest.mark.parametrize("numeral,key,expected", [
    ("ii-7",   Notes.F,  "G-7"),
    ("V7",     Notes.Bb, "F7"),
    ("bVI^7",  Notes.C,  "Ab^7"),
    ("#IVo7",  Notes.C,  "Gbo7"),
    ("bII7",   Notes.E,  "F7"),
    ("bII7",   Notes.C,  "Db7"),
    ("bIII^7", Notes.C,  "Eb^7"),
    ("iih7",   Notes.C,  "Dh7"),
])
def test_chord_in_key_golden(numeral, key, expected):
    assert _ck(numeral, key) == expected


def test_chord_in_key_halfdim_pitch_set():
    from music_dsl.realize import chord_pitches
    pitches = chord_pitches(chord_in_key(NumericChord.from_chord_string("iih7"), Notes.C), 4)
    root = pitches[0]
    assert [p - root for p in pitches] == [0, 3, 6, 10]


@pytest.mark.parametrize("numeral,key,expected", [
    ("V7/V",  Notes.C, "D7"),
    ("V7/ii", Notes.C, "A7"),
    ("V7/IV", Notes.C, "C7"),
])
def test_chord_in_key_slash(numeral, key, expected):
    assert _ck(numeral, key) == expected


def test_numericchord_in_key_delegates():
    n = NumericChord.from_chord_string("V7/V")
    assert n.in_key(Notes.C)._chord_str == "D7"   # ._chord_str, not repr (which wraps)


_REPRESENTABLE_KEYS = [Notes.C, Notes.Db, Notes.D, Notes.Eb, Notes.E, Notes.F,
                       Notes.Gb, Notes.G, Notes.Ab, Notes.A, Notes.Bb, Notes.B]

_DEGREES = ["I^7", "ii-7", "iii-7", "IV^7", "V7", "vi-7", "iih7",
            "i-7", "iv-7", "bII7", "bIII^7", "bVI^7", "bVII7",
            "V7/V", "V7/ii", "V7/IV", "V7/vi", "#IVo7"]


@pytest.mark.parametrize("degree", _DEGREES)
def test_chord_in_key_representable_in_all_keys(degree):
    from music_dsl.realize import chord_pitches
    n = NumericChord.from_chord_string(degree)
    for key in _REPRESENTABLE_KEYS:
        chord = chord_in_key(n, key)
        pitches = chord_pitches(chord, 4)
        assert len(pitches) >= 3 and all(isinstance(p, int) for p in pitches)
