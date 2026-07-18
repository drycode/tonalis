"""DRY-426: object-contract invariants the per-op conformance suite is blind to.

These property tests guard the two bug classes that actually bit us:
  * eq/hash contract  (DRY-407 P0s)
  * repr purity / construction-order independence  (DRY-425 singleton aliasing)
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from music_dsl.builders import build_from_chord_string
from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.numeric_chord import NumericChord
from tests.testdata.fuzzy_test_supersets import (
    EXAMPLE_MULTI_DIM_CHORDS,
    EXAMPLE_NUMERIC_STRS,
)
from tests.testdata.other_intentional import EXAMPLE_CHORD_STRS


def _numeric(s):
    return build_from_chord_string(s, NumericChord)


# --- eq/hash contract (guards DRY-407) -------------------------------------

@given(st.sampled_from(EXAMPLE_CHORD_STRS), st.sampled_from(EXAMPLE_CHORD_STRS))
def test_chord_eq_implies_hash_eq(a_str, b_str):
    a, b = Chord(a_str), Chord(b_str)
    if a == b:
        assert hash(a) == hash(b), (a_str, b_str)


@given(st.sampled_from(EXAMPLE_CHORD_STRS))
def test_chord_eq_hash_are_deterministic(s):
    # Building the "same" chord twice must be equal and hash equal (also exercises
    # the singleton path — a from_attrs-built instance must stay hashable).
    a, b = Chord(s), Chord(s)
    assert a == b
    assert hash(a) == hash(b)


@given(st.sampled_from(EXAMPLE_NUMERIC_STRS + EXAMPLE_MULTI_DIM_CHORDS),
       st.sampled_from(EXAMPLE_NUMERIC_STRS + EXAMPLE_MULTI_DIM_CHORDS))
def test_numeric_eq_implies_hash_eq(a_str, b_str):
    a, b = _numeric(a_str), _numeric(b_str)
    if a == b:
        assert hash(a) == hash(b), (a_str, b_str)


# --- repr idempotence (a chord's repr re-parses to the same repr) ----------

@given(st.sampled_from(EXAMPLE_CHORD_STRS))
def test_chord_canonical_string_round_trips(s):
    # The canonical serialization (chord_attrs repr, what the codec uses) must
    # re-parse to itself. NOTE: Chord.__repr__/__str__ is a debug form
    # ("<Chord Ab^7>") and is intentionally NOT tested here — see the DRY-426
    # note about the Chord-vs-NumericChord repr inconsistency.
    canonical = repr(Chord(s)._chord_attrs)
    assert repr(Chord(canonical)._chord_attrs) == canonical


@given(st.sampled_from(EXAMPLE_NUMERIC_STRS + EXAMPLE_MULTI_DIM_CHORDS))
def test_numeric_repr_is_idempotent(s):
    once = str(_numeric(s))
    assert str(_numeric(once)) == once


# --- repr purity / construction-order independence (guards DRY-425) --------

@settings(max_examples=200)
@given(
    st.lists(st.sampled_from(EXAMPLE_NUMERIC_STRS + EXAMPLE_MULTI_DIM_CHORDS),
             min_size=0, max_size=10),
    st.sampled_from(EXAMPLE_NUMERIC_STRS + EXAMPLE_MULTI_DIM_CHORDS),
)
def test_numeric_repr_is_construction_order_independent(noise, target):
    # A chord's repr must not depend on what else was built before it — the exact
    # failure mode of the singleton-cache aliasing bug.
    baseline = str(_numeric(target))
    for s in noise:
        _numeric(s)
    assert str(_numeric(target)) == baseline
