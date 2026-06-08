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
