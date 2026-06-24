import pytest

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
from music_dsl.domain.static import Extensions, Notes, Seventh, Triad
from tests.testdata.other_intentional import EXAMPLE_CHORDS


@pytest.mark.parametrize("_input, expected", EXAMPLE_CHORDS)
def test_parse_chord(_input, expected):
    parsed = Chord._parse_chord_string(_input)
    assert expected.root == parsed.root
    assert expected.triad == parsed.triad
    assert expected._7th == parsed._7th


@pytest.mark.parametrize("_input", ["AA", "H-7", "A|B|C", "", "Z7"])
def test_invalid_chord_strings(_input):
    """
    Assert specific exceptions raised for all variations of invalid chord string
    inputs. This feature is not yet supported for the Chord class.
    """
    with pytest.raises(InvalidChordStringException):
        Chord(_input)


def test_augmented_triad():
    """An augmented triad ("+") parses with a major 3rd and an augmented 5th."""
    chord = Chord("F+")
    assert chord.root == Notes("F")
    assert chord.triad == Triad.Augmented
    assert chord._7th == Seventh._None
    # major 3rd (bit 4) + augmented 5th (bit 8) set in the encoding
    assert chord.encoding & (1 << (19 - (4 + 1)))
    assert chord.encoding & (1 << (19 - (8 + 1)))


def test_altered_dominant():
    """"7alt" parses as a dominant 7 carrying the alt tension set."""
    chord = Chord("A7alt")
    assert chord.root == Notes("A")
    assert chord._7th == Seventh.Minor
    assert Extensions.alt in chord.extensions
    # also valid for various roots and accidentals
    for token in ("E7alt", "Bb7alt", "C#7alt", "Ab7alt"):
        assert Chord(token)._7th == Seventh.Minor


@pytest.mark.parametrize(
    "token, expected_triad, expected_7th",
    [
        ("F9sus", Triad.Sus, Seventh._None),
        ("G7b9sus", Triad.Sus, Seventh.Minor),
        ("Eb13sus", Triad.Sus, Seventh._None),
        ("C7b9sus", Triad.Sus, Seventh.Minor),
        # canonical mid-position sus + extension (e.g. Bb7sus#9)
        ("Bb7sus#9", Triad.Sus, Seventh.Minor),
        ("Bb7sus4#9", Triad.Sus4, Seventh.Minor),
    ],
)
def test_sus_with_extensions(token, expected_triad, expected_7th):
    """Sus chords may carry extensions in either lead-sheet position."""
    chord = Chord(token)
    assert chord.triad == expected_triad
    assert chord._7th == expected_7th


@pytest.mark.parametrize(
    "token, expected_exts",
    [
        ("Gadd9", (Extensions.add9,)),
        ("G69", (Extensions.add6, Extensions.add9)),
        ("G-b6", (Extensions.b6,)),
        ("G2", (Extensions.add2,)),
        ("C#5", (Extensions.add5,)),
    ],
)
def test_extension_grammar(token, expected_exts):
    """add9 / 69 / b6 / bare 2 & 5 tokens parse into the right extensions."""
    assert Chord(token).extensions == expected_exts


def test_bare_major_seventh_shorthand():
    """"C^" is shorthand for the major-7th chord "C^7"."""
    assert Chord("C^")._7th == Seventh.Major
    assert Chord("C^").encoding == Chord("C^7").encoding


@pytest.mark.parametrize(
    "token, expected_root",
    [("Cb", Notes("B")), ("Fb", Notes("E")), ("B#", Notes("C")), ("E#", Notes("F"))],
)
def test_white_key_enharmonic_roots(token, expected_root):
    """White-key enharmonic spellings normalise to their pitch."""
    assert Chord(token).root == expected_root
