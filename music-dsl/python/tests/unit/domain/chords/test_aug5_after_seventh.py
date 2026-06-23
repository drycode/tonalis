"""iReal ``X7+`` means a dominant 7 with a raised 5th (``X7#5``).

In iReal Pro notation a ``+`` glued AFTER a numeric seventh raises the fifth: ``C7+`` is
``C7#5`` (dominant 7, augmented 5th), NOT an augmented triad. The augmented-triad ``+``
appears BEFORE the seventh (``C+``, ``C+7``); that long-standing semantic must be
preserved. MusicDSL is the source of truth for what a chord is, and ``7+`` is a real
iReal chord form the permissive linter regex used to accept, so MusicDSL must construct
it identically to the canonical ``7#5`` spelling.
"""

import pytest

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.static import Extensions, Seventh, Triad


@pytest.mark.parametrize("root", ["C", "G", "A", "D", "E", "F", "B"])
def test_seven_plus_is_seven_sharp_five(root):
    """``X7+`` constructs the SAME chord as ``X7#5`` (dominant 7, raised 5th)."""
    seven_plus = Chord(f"{root}7+")
    seven_sharp_five = Chord(f"{root}7#5")
    assert seven_plus.triad == Triad.Major, seven_plus.triad
    assert seven_plus._7th == Seventh.Minor
    assert Extensions.s5 in seven_plus.extensions
    assert seven_plus == seven_sharp_five
    assert seven_plus.encoding == seven_sharp_five.encoding


@pytest.mark.parametrize("token", ["Bb7+", "Eb7+", "Ab7+", "F#7+", "Db7+"])
def test_seven_plus_accidental_roots(token):
    """``X7+`` works for accidental roots too (these appear in the conformance corpus)."""
    chord = Chord(token)
    assert chord.triad == Triad.Major
    assert chord._7th == Seventh.Minor
    assert Extensions.s5 in chord.extensions


@pytest.mark.parametrize("token", ["Bb7+/F", "C7+/G", "Eb7+/Bb"])
def test_seven_plus_slash_bass(token):
    """``X7+/bass`` parses (the slash bass is discarded like every slash chord)."""
    chord = Chord(token)
    assert chord.triad == Triad.Major
    assert chord._7th == Seventh.Minor
    assert Extensions.s5 in chord.extensions


def test_augmented_triad_forms_unchanged():
    """A ``+`` BEFORE the seventh stays an augmented triad; ``7+`` must NOT cannibalize it."""
    assert Chord("C+").triad == Triad.Augmented
    assert Chord("C+")._7th == Seventh._None
    assert Chord("C+7").triad == Triad.Augmented
    assert Chord("C+7")._7th == Seventh.Minor


def test_plain_forms_unchanged():
    """Plain sevenths / sixths / altered tensions are untouched by the ``7+`` teaching."""
    assert Chord("C7").triad == Triad.Major
    assert Chord("C7")._7th == Seventh.Minor
    assert Chord("C7").extensions == ()
    assert Chord("C6").triad == Triad.Major
    assert Chord("C6").extensions == (Extensions.add6,)
    assert Chord("C7b9")._7th == Seventh.Minor
    assert Extensions.b9 in Chord("C7b9").extensions
    # the canonical raised-5th spelling is itself unchanged
    assert Extensions.s5 in Chord("C7#5").extensions
