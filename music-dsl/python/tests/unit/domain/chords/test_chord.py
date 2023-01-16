import pytest

from music_dsl.domain.chords.chord import Chord
from tests.testdata.other_intentional import EXAMPLE_CHORDS


@pytest.mark.parametrize("_input, expected", EXAMPLE_CHORDS)
def test_parse_chord(_input, expected):
    parsed = Chord._parse_chord_string(_input)
    assert expected.root == parsed.root
    assert expected.triad == parsed.triad
    assert expected._7th == parsed._7th
