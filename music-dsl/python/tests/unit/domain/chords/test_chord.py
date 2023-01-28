import pytest

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
from tests.testdata.other_intentional import EXAMPLE_CHORDS


@pytest.mark.parametrize("_input, expected", EXAMPLE_CHORDS)
def test_parse_chord(_input, expected):
    parsed = Chord._parse_chord_string(_input)
    assert expected.root == parsed.root
    assert expected.triad == parsed.triad
    assert expected._7th == parsed._7th


@pytest.mark.parametrize("_input", ["AA", "H-7", "A|B|C"])
def test_invalid_chord_strings(_input):
    """
    Assert specific exceptions raised for all variations of invalid chord string
    inputs. This feature is not yet supported for the Chord class.
    """
    with pytest.raises(InvalidChordStringException):
        Chord(_input)
