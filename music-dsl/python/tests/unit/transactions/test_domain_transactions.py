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
from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
from music_dsl.transactions import (
    harmonic_function_in_key,
    is_diatonic,
    modulate,
)
from music_dsl.domain.static import HarmonicFunctions

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
        try:
            _new = build_chord(
                root=root, triad=triad, _7th=_7th, extensions=tuple(extensions)
            )
        except InvalidChordStringException:
            # An unspellable component combo (natural root + bare major triad +
            # leading flat/sharp tension + no 7th, e.g. C + b9) is legitimately
            # rejected -- the accidental would bind to the root in its repr.
            return
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
        ((Notes.Bb, Scales.Major, Chord("Bb")), True),
    ],
)
def test_is_diatonic_to_Major(_input, expected):
    assert is_diatonic(*_input) == expected


@pytest.mark.parametrize(
    ["_input", "expected"],
    [
        # Natural-minor diatonic chords of C minor
        ((Notes.C, Scales.Minor, Chord("C-7")), True),
        ((Notes.C, Scales.Minor, Chord("Dh7")), True),
        ((Notes.C, Scales.Minor, Chord("Eb^7")), True),
        ((Notes.C, Scales.Minor, Chord("F-7")), True),
        ((Notes.C, Scales.Minor, Chord("G-7")), True),
        ((Notes.C, Scales.Minor, Chord("Ab^7")), True),
        ((Notes.C, Scales.Minor, Chord("Bb7")), True),
        # The dominant V7 needs the raised 7th (harmonic minor), so it is NOT
        # diatonic to natural minor.
        ((Notes.C, Scales.Minor, Chord("G7")), False),
        ((Notes.C, Scales.Minor, Chord("C^7")), False),
        # Harmonic-minor: the V7 becomes diatonic.
        ((Notes.C, Scales.HarmonicMinor, Chord("G7")), True),
        ((Notes.C, Scales.HarmonicMinor, Chord("C-7")), False),
    ],
)
def test_is_diatonic_to_Minor(_input, expected):
    assert is_diatonic(*_input) == expected


@pytest.mark.parametrize(
    ["key_root", "key_is_minor", "chord", "expected"],
    [
        # Minor tonic: the i-7 of a minor key is Tonic (quality-only mapping
        # would call it Subdominant).
        (Notes.C, True, Chord("C-7"), HarmonicFunctions.Tonic),
        # Other minor-key degrees keep their quality-based function.
        (Notes.C, True, Chord("Dh7"), HarmonicFunctions.Subdominant),
        (Notes.C, True, Chord("F-7"), HarmonicFunctions.Subdominant),
        (Notes.C, True, Chord("G7"), HarmonicFunctions.Dominant),
        # Major key: the tonic-degree change is a no-op; behavior matches the
        # quality-only mapping.
        (Notes.C, False, Chord("C^7"), HarmonicFunctions.Tonic),
        (Notes.C, False, Chord("D-7"), HarmonicFunctions.Subdominant),
        (Notes.C, False, Chord("G7"), HarmonicFunctions.Dominant),
        # A blues I7 (dominant quality on the tonic degree) keeps its quality so
        # it can still be labeled I7, even in a minor-key context.
        (Notes.Bb, False, Chord("Bb7"), HarmonicFunctions.Dominant),
    ],
)
def test_harmonic_function_in_key(key_root, key_is_minor, chord, expected):
    assert harmonic_function_in_key(key_root, key_is_minor, chord) == expected


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
