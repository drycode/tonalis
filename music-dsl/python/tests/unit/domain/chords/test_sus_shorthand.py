"""Sus shorthand (common lead-sheet notation): a bare ``4`` immediately after the root is sus4.

Lead-sheet notation writes ``C4`` for a C sus4 chord (the "4" is the suspended fourth, NOT an
added/extension degree). MusicDSL must construct ``C4`` identically to ``Csus`` (and
``Csus4`` — a bare ``sus`` defaults to sus4). The slash-bass form ``A4/C``
must also parse (sus4 with the bass discarded, mirroring every other slash chord).

The companion bare ``2`` shorthand is intentionally NOT remapped here: ``C2`` already
parses as a major chord with an added 2nd (``Extensions.add2``) — a long-standing,
explicitly-tested MusicDSL semantic (see ``test_extension_grammar``: ``("G2",
(Extensions.add2,))``). ``2`` is therefore never a validity divergence against the old
linter grammar (both accept it), so the reconciliation oracle is unaffected and there
is no need — and no licence — to silently change its meaning.
"""

import pytest

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.static import Seventh, Triad


@pytest.mark.parametrize("root", ["C", "G", "A", "D", "E", "F", "B"])
def test_bare_four_is_sus4(root):
    """``X4`` constructs the SAME chord as ``Xsus4`` (sus shorthand, common lead-sheet notation).

    It is also musically identical to the bare ``Xsus`` (which defaults to
    sus4): the two carry distinct triad enums (``Sus4`` vs the bare ``Sus``) — a
    pre-existing MusicDSL distinction — but encode the exact same pitch set.
    """
    four = Chord(f"{root}4")
    sus = Chord(f"{root}sus")
    sus4 = Chord(f"{root}sus4")
    assert four.triad == Triad.Sus4, four.triad
    assert four._7th == Seventh._None
    # X4 IS sus4 (exact equality), and musically identical to the bare sus (same pitches)
    assert four == sus4
    assert four.encoding == sus4.encoding == sus.encoding


@pytest.mark.parametrize("token", ["A#4", "Bb4", "C#4", "D#4", "Gb4", "E#4", "Db4"])
def test_bare_four_with_accidental_root(token):
    """``X4`` works for accidental roots too (these appear in the conformance corpus)."""
    chord = Chord(token)
    assert chord.triad == Triad.Sus4
    assert chord._7th == Seventh._None


@pytest.mark.parametrize("token", ["A4/C", "D4/B", "E4/G", "Db4/D#"])
def test_bare_four_with_slash_bass(token):
    """``X4/bass`` parses (sus4; the slash bass is discarded like every slash chord)."""
    chord = Chord(token)
    assert chord.triad == Triad.Sus4
    assert chord._7th == Seventh._None


def test_real_extension_degrees_unchanged():
    """The teaching must NOT disturb real extension degrees (6/7/9/11/13/69) or the
    deliberate ``2`` (add2) / ``5`` (add5) semantics, nor existing sus forms."""
    from music_dsl.domain.static import Extensions

    assert Chord("C6").triad == Triad.Major
    assert Chord("C7")._7th == Seventh.Minor
    assert Chord("C9").extensions == (Extensions.add9,)
    assert Chord("C11").extensions == (Extensions.add11,)
    assert Chord("C13").extensions == (Extensions.add13,)
    assert Chord("C69").extensions == (Extensions.add6, Extensions.add9)
    # bare 2/5 stay added degrees (long-standing, tested semantics)
    assert Chord("C2").triad == Triad.Major
    assert Chord("C2").extensions == (Extensions.add2,)
    assert Chord("C5").extensions == (Extensions.add5,)
    # existing sus forms unaffected
    assert Chord("Csus").triad == Triad.Sus
    assert Chord("Gsus4").triad == Triad.Sus4
    assert Chord("F9sus").triad == Triad.Sus
    assert Chord("C7b9sus")._7th == Seventh.Minor
