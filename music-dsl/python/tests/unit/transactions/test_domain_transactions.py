from typing import Set

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from music_dsl.encode import Scales
from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.numeric_chord import NumericChord, build_numeric_chord
from music_dsl.domain.static import (
    Intervals,
    Notes,
    ScaleDegree,
    Seventh,
    SupportedExtensions,
    Triad,
)


from music_dsl.builders import build_chord
from music_dsl.transactions import is_diatonic, modulate

instances: Set[NumericChord] = set()


@given(
    root=st.sampled_from(ScaleDegree),
    triad=st.sampled_from(Triad),
    _7th=st.sampled_from(Seventh),
    extensions=st.permutations(SupportedExtensions),
)
def test_fuzz_build_numeric_chord(root, triad, _7th, extensions):
    if not isinstance(root.value, dict):
        _new = build_numeric_chord(
            root=root, triad=triad, _7th=_7th, extensions=tuple(extensions)
        )
        assume(_new not in instances)


@given(
    root=st.sampled_from(Notes),
    triad=st.sampled_from(Triad),
    _7th=st.sampled_from(Seventh),
    extensions=st.permutations(SupportedExtensions),
)
# @settings(max_examples=20000)
def test_fuzz_build_chord(root, triad, _7th, extensions):
    if not isinstance(root.value, dict):
        _new = build_chord(
            root=root, triad=triad, _7th=_7th, extensions=tuple(extensions)
        )
        assume(_new not in instances)


@pytest.mark.parametrize(
    ["_input", "expected"],
    [
        ((Notes.C, Scales.Major, Chord("D-7")), True),
        ((Notes.C, Scales.Major, Chord("E-7")), True),
        ((Notes.C, Scales.Major, Chord("F-7")), False),
        ((Notes.C, Scales.Major, Chord("F^7")), True),
        ((Notes.D, Scales.Major, Chord("C#h7")), True),
        ((Notes.D, Scales.Major, Chord("Dbh7")), True),
        ((Notes.D, Scales.Major, Chord("Dbh7")), True),
        ((Notes.D, Scales.Major, Chord("D^7")), True),
        ((Notes.D, Scales.Major, Chord("D-7")), False),
        ((Notes.D, Scales.Major, Chord("F#-")), True),
        ((Notes.Fs, Scales.Major, Chord("D-7")), False),
        ((Notes.C, Scales.Major, Chord("Bh7")), True),
        ((Notes.C, Scales.Major, Chord("E7b9")), False),
    ],
)
def test_is_diatonic_to_Major(_input, expected):
    assert is_diatonic(*_input) == expected


@pytest.mark.parametrize(
    ["semitones", "starting_note", "expected"],
    [
        (Intervals.Octave.up(), Notes.C, Notes.C),
        (Intervals.M7.up(), Notes.C, Notes.B),
        (Intervals.m7.up(), Notes.C, Notes.Bb),
        (Intervals.M6.up(), Notes.C, Notes.A),
        (Intervals.m6.up(), Notes.C, Notes.Ab),
        (Intervals.P5.up(), Notes.C, Notes.G),
        (Intervals.Tritone.up(), Notes.C, Notes.Fs),
        (Intervals.P4.up(), Notes.C, Notes.F),
        (Intervals.M3.up(), Notes.C, Notes.E),
        (Intervals.m3.up(), Notes.C, Notes.Ds),
        (Intervals.M2.up(), Notes.C, Notes.D),
        (Intervals.m2.up(), Notes.C, Notes.Cs),
        (Intervals.Unison.down(), Notes.C, Notes.C),
        (Intervals.m2.down(), Notes.C, Notes.B),
        (Intervals.M2.down(), Notes.C, Notes.Bb),
        (Intervals.m3.down(), Notes.C, Notes.A),
        (Intervals.M3.down(), Notes.C, Notes.Ab),
        (Intervals.P4.down(), Notes.C, Notes.G),
        (Intervals.Tritone.down(), Notes.C, Notes.Fs),
        (Intervals.P5.down(), Notes.C, Notes.F),
        (Intervals.m6.down(), Notes.C, Notes.E),
        (Intervals.M6.down(), Notes.C, Notes.Eb),
        (Intervals.m7.down(), Notes.C, Notes.D),
        (Intervals.M7.down(), Notes.C, Notes.Db),
        (Intervals.Octave.down(), Notes.C, Notes.C),
    ],
)
def test_modulate(semitones: Intervals, starting_note: Notes, expected: Notes):
    assert modulate(semitones, starting_note) == expected
