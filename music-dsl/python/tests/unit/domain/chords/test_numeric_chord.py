from music_dsl.domain.chords.abstract_chord import ChordAttrs
from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.numeric_chord import NumericChord
from music_dsl.domain.static import (
    Notes,
    HarmonicFunctions,
    Seventh,
    Triad,
    ScaleDegree,
)

from pytest import mark

from music_dsl.domain.static.chord import Extensions


def test_singleton_impl():
    assert NumericChord.from_chord_string("V7/V") is NumericChord.from_chord_string(
        "V7/V"
    )

    assert NumericChord(Notes.C, Chord("F7"), Chord("Bb7")) is NumericChord(
        Notes.C, Chord("F7"), Chord("Bb7")
    )


def test_resolves_to_self():
    x = NumericChord(Notes.C, Chord("C"), Chord("C"))
    assert not x.denominator


def test_resolution_is_not_self():
    x = NumericChord(Notes.C, Chord("F7"), Chord("Bb7"))
    assert x is not x.denominator
    assert repr(x) == "V7/bVII7"


def test_resolution_to_self():
    x = NumericChord(Notes.C, Chord("E-7"), Chord("D-7"))
    assert x is not x.denominator
    assert repr(x) == "ii-7/ii-7"


@mark.parametrize(
    "chord_str, attrs",
    [
        (
            "V/V",
            ChordAttrs(
                ScaleDegree.V,
                Triad.Major,
                Seventh._None,
                (),
                HarmonicFunctions.Tonic,
                False,
            ),
        ),
        (
            "sV/V",
            ChordAttrs(
                ScaleDegree.V,
                Triad.Major,
                Seventh._None,
                (),
                HarmonicFunctions.Tonic,
                True,
            ),
        ),
    ],
)
def test_from_chord_string(chord_str, attrs):
    x = NumericChord.from_chord_string(chord_str)
    assert x._chord_attrs == attrs


def test_chords_not_equal():
    assert NumericChord.from_chord_string("ii-7/V7") != NumericChord.from_chord_string(
        "V7/ii-7"
    )
