"""Tests for Measure beat construction, especially the multi-chord-measure case.

The legacy ``Measure._setup_beats`` allocated a fixed-size array of
``time_signature.denominator`` slots and wrote one slot per chord-beat. A measure
that expanded to more chord-beats than the denominator (e.g. ``F^7 Eh A7`` -> 5
beats in 4/4) overflowed the array with an ``IndexError``. The padding loop was
also off-by-one and reused the stale loop variable. These tests pin the fixed
behaviour.
"""

import pytest

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.time import TimeSignature
from music_dsl.domain.time.measure import BeatType, Measure


def _make(raw, ts=TimeSignature(4, 4)):
    return Measure(0, ts, raw, BeatType, chord_type=Chord)


def _chord_strs(measure):
    return [bc.chord._chord_str if bc else None for bc in measure.beat_containers]


def test_full_bar_single_chord_pads_to_denominator():
    measure = _make("C^7")
    assert len(measure.beat_containers) == 4
    assert _chord_strs(measure) == ["C^7", "C^7", "C^7", "C^7"]


def test_two_chords_split_evenly():
    measure = _make("A-7 D7")
    assert len(measure.beat_containers) == 4
    assert _chord_strs(measure) == ["A-7", "A-7", "D7", "D7"]


def test_multi_chord_measure_does_not_overflow():
    """Three chords expanding to five beats must not raise IndexError."""
    measure = _make("F^7 Eh A7")
    # array grows to accommodate the 5 beats rather than overflowing 4 slots
    assert len(measure.beat_containers) == 5
    assert _chord_strs(measure) == ["F^7", "F^7", "Eh", "Eh", "A7"]


def test_five_chord_measure():
    measure = _make("C^7 A-7 D-7 G7 C^7")
    assert len(measure.beat_containers) == 9
    assert _chord_strs(measure)[-1] == "C^7"
    # no None slots remain
    assert all(bc is not None for bc in measure.beat_containers)


def test_beat_locations_are_sequential():
    measure = _make("F^7 Eh A7")
    assert [bc.beat_location.beat_number for bc in measure.beat_containers] == [
        0,
        1,
        2,
        3,
        4,
    ]


def test_padding_uses_last_chord_not_loop_variable():
    """A short measure pads remaining slots with the LAST chord seen."""
    measure = _make("C^7 D-7")
    assert _chord_strs(measure) == ["C^7", "C^7", "D-7", "D-7"]
