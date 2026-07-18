"""DRY-425: singleton-cache identity must be collision-safe (repr string, not hash(int)).

The __instances__ cache was keyed by hash(repr(...)); Python's str hash is randomized
per process, so distinct chords whose reprs collided aliased to one cache slot and leaked
_denominator across chords — making NumericChord repr order-dependent (flaky), e.g.
I7b5/iii intermittently rendering I7b5/iii/ii.
"""

from music_dsl.domain.chords.abstract_chord import AbstractChord
from music_dsl.domain.chords.numeric_chord import NumericChord


def test_singleton_key_is_a_string():
    attrs = NumericChord.from_chord_string("iii")._chord_attrs
    assert isinstance(AbstractChord._singleton_key(attrs), str)


def test_plain_and_slash_degree_have_distinct_keys():
    plain = NumericChord.from_chord_string("iii")
    slash = NumericChord.from_chord_string("V7/iii")
    k_plain = AbstractChord._singleton_key(plain._chord_attrs)
    k_slash = AbstractChord._singleton_key(
        slash._chord_attrs, slash.denominator._chord_attrs
    )
    assert k_plain != k_slash
    assert isinstance(k_slash, str)


def test_numeric_repr_is_order_independent():
    # Build chords that put a denominator on 'iii'; the plain-'iii' singleton must not
    # inherit a stale denominator that then corrupts an unrelated slash chord's repr.
    NumericChord.from_chord_string("V7/iii")
    NumericChord.from_chord_string("iii/ii")
    assert str(NumericChord.from_chord_string("I7b5/iii")) == "I7b5/iii"
    assert str(NumericChord.from_chord_string("iii")) == "iii"
