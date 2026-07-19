"""NumericChord slash-denominator eq/hash contract (regression, found pre-v0.1.0).

The old NumericChord __eq__ ignored the denominator whenever the LEFT side's was
I-or-missing — making X/V == X and X/I == X/V hold one-directionally (asymmetric,
non-transitive) — while __hash__ hashed the full repr key including the
denominator. Caught by the DRY-426 hypothesis invariants on the enharmonic pair
('#I-^7b5', 'bii-^7b5/I'). Identity now quotients a tonic-degree denominator to
None in one shared tuple.
"""

from music_dsl.builders import build_from_chord_string
from music_dsl.domain.chords.numeric_chord import NumericChord


def _n(s):
    return build_from_chord_string(s, NumericChord)


def test_tonic_denominator_is_canonical_no_denominator():
    # The pair hypothesis caught: enharmonic numerator roots, one with /I.
    a, b = _n("#I-^7b5"), _n("bii-^7b5/I")
    assert a == b and b == a
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_non_tonic_denominator_distinguishes():
    plain, over_five = _n("II7"), _n("II7/V")
    assert plain != over_five
    assert over_five != plain  # the old code was asymmetric here


def test_distinct_denominators_distinguish_transitively():
    over_one, over_five = _n("II7/I"), _n("II7/V")
    plain = _n("II7")
    assert over_one == plain
    assert hash(over_one) == hash(plain)
    assert over_one != over_five  # old code: equal one-directionally via plain
    assert over_five != over_one


def test_same_denominator_root_equal():
    assert _n("II7/V") == _n("II7/V")
    assert hash(_n("II7/V")) == hash(_n("II7/V"))
