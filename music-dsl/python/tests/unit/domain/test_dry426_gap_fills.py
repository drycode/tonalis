"""DRY-426 #2/#3: unit tests for previously-uncovered public functions + error-type pinning.

These pin the Python error *types* (not just "an error was raised", which is all the
conformance cases assert) and cover the live functions the conformance suite doesn't reach.
"""

import math

import pytest

from music_dsl.builders import build_from_chord_string
from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.numeric_chord import NumericChord
from music_dsl.domain.static import Notes
from music_dsl.encode import NonFunctionalScaleError, Scales
from music_dsl.realize import note_to_hz
from music_dsl.transactions import is_diatonic


def test_note_to_hz_reference_pitches():
    assert math.isclose(note_to_hz(Notes.A, octave=4), 440.0, rel_tol=1e-9)
    # An octave up doubles the frequency.
    assert math.isclose(note_to_hz(Notes.A, octave=5), 880.0, rel_tol=1e-9)


# --- error TYPES (conformance only asserts "some error"; pin the specific type) ---

def test_is_diatonic_raises_non_functional_scale_error():
    with pytest.raises(NonFunctionalScaleError):
        is_diatonic(Notes.C, Scales.WholeTone, Chord("C"))
    with pytest.raises(NonFunctionalScaleError):
        is_diatonic(Notes.C, Scales.Chromatic, Chord("C"))


def test_invalid_chord_string_raises_invalid_chord_string_exception():
    with pytest.raises(InvalidChordStringException):
        Chord("xyzzy")


def test_build_from_chord_string_rejects_unknown_parser_type():
    with pytest.raises(ValueError):
        build_from_chord_string("C", parser_type=object)


def test_build_from_chord_string_dispatches_both_parsers():
    assert isinstance(build_from_chord_string("C^7", Chord), Chord)
    assert isinstance(build_from_chord_string("V7", NumericChord), NumericChord)
