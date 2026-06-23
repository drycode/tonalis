import pytest
from collections import namedtuple
from music_dsl.domain.static import MAJOR_HARMONIC_FUNCTIONS, Notes
from music_dsl.domain.static.notes import TWELVE_TONES, Intervals
from music_dsl.helpers import get_index, semitones_apart_ascending

Pair = namedtuple("Pair", "note1, note2")


@pytest.mark.parametrize(
    "pairs",
    [
        Pair(Notes.C, Notes.E),
        Pair(Notes.C, Notes.A),
    ],
)
def test_semitones_apart_in_tonic(pairs):
    for i in range(12):
        assert (
            semitones_apart_ascending(
                TWELVE_TONES[(get_index(pairs.note1) + i) % 12],
                TWELVE_TONES[(get_index(pairs.note2) + i) % 12],
            )
            in MAJOR_HARMONIC_FUNCTIONS.tonic
        )
