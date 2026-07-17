"""Regression tests for the DRY-407 P0 correctness fixes.

1. Lookup maps declared inside the Notes/ScaleDegree Enum bodies used to become
   members, polluting iteration and len().
2. Chord.__hash__ hashed repr(chord_attrs) (including extensions) while __eq__
   omitted extensions, violating the eq/hash contract.
"""

from music_dsl.domain.static import Notes, ScaleDegree
from music_dsl.domain.chords.chord import Chord


def test_enums_not_polluted_by_lookup_maps():
    assert len(Notes) == 17
    assert len(ScaleDegree) == 34
    assert all(isinstance(n.value, str) for n in Notes)
    assert all(isinstance(d.value, str) for d in ScaleDegree)


def test_chord_eq_includes_extensions():
    # These were spuriously equal before the fix (extensions ignored by __eq__).
    assert Chord("C") != Chord("Cadd9")
    assert Chord("C9") != Chord("C13")


def test_chord_eq_hash_are_consistent():
    # Equal chords must hash equal; the pre-fix hash used extensions but eq did not.
    assert Chord("C") == Chord("C")
    assert hash(Chord("C9")) == hash(Chord("C9"))
    # Enharmonic roots normalize to one spelling, so they stay equal AND hash-equal.
    a, b = Chord("C#"), Chord("Db")
    assert a == b
    assert hash(a) == hash(b)


def test_chord_eq_foreign_type_is_false_not_error():
    assert (Chord("C") == "C") is False
    assert (Chord("C") == 42) is False
