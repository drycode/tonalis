from music_dsl.domain.static import Intervals


def test_interval_equals_only_itself():
    assert Intervals.m6 == Intervals.m6
    # an interval is NOT equal to its inversion (m6 != M3, m2 != M7, P4 != P5)
    assert Intervals.m6 != Intervals.M3
    assert Intervals.m2 != Intervals.M7
    assert Intervals.P4 != Intervals.P5
    assert Intervals.Unison != Intervals.Octave


def test_interval_compares_to_plain_int():
    # Intervals subclasses int; comparing to an int must not raise.
    assert Intervals.m6 == 8
    assert 8 == Intervals.m6
    assert Intervals.m6 != 4


def test_interval_eq_hash_consistent():
    # equal intervals hash equal; the (former) inversion pair now hashes apart
    assert hash(Intervals.m6) == hash(Intervals(8))
    assert hash(Intervals.m6) != hash(Intervals.M3)


def test_branch3_guard_is_structural():
    # the exact expression numeric_chord branch 3 evaluates
    assert (Intervals(8) == Intervals.m6) is True   # genuine m6 root motion
    assert (Intervals(4) == Intervals.m6) is False  # M3 (inversion) must NOT match
