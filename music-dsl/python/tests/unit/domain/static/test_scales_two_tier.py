"""DRY-411: Scale descriptor + two-tier diatonicity API (reference implementation)."""

import pytest

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.static import Notes
from music_dsl.encode import (
    NonFunctionalScaleError,
    ScaleDescriptor,
    Scales,
    contains,
)
from music_dsl.transactions import is_diatonic


def test_scales_carry_descriptors():
    d = Scales.Major.value
    assert isinstance(d, ScaleDescriptor)
    assert d.mask == int("101011010101" * 3, 2)
    assert d.name == "Major (Ionian)"
    assert d.category == "major"
    assert d.supports_diatonic_function is True
    # The three original scales are functional (the catalog also has non-functional
    # symmetric scales — see test_scale_catalog).
    assert Scales.Major.value.supports_diatonic_function
    assert Scales.Minor.value.supports_diatonic_function
    assert Scales.HarmonicMinor.value.supports_diatonic_function


def test_contains_membership_major():
    present = {0, 2, 4, 5, 7, 9, 11}  # major scale pitch classes
    assert [pc for pc in range(12) if contains(Scales.Major, pc)] == sorted(present)


def test_contains_membership_natural_minor():
    present = {0, 2, 3, 5, 7, 8, 10}  # natural minor pitch classes
    assert [pc for pc in range(12) if contains(Scales.Minor, pc)] == sorted(present)


def test_contains_wraps_octave():
    assert contains(Scales.Major, 12) == contains(Scales.Major, 0)
    assert contains(Scales.Major, 14) == contains(Scales.Major, 2)


def test_is_diatonic_still_works_on_functional_scales():
    # Migration smoke check: functional scales still answer (no refusal).
    result = is_diatonic(Notes.C, Scales.Major, Chord("C"))
    assert isinstance(result, bool)


def test_is_diatonic_refuses_non_functional_scale():
    # DRY-412 adds real non-functional scales; here we exercise the refusal path
    # with a duck-typed stand-in carrying a non-functional descriptor.
    class _FakeSymmetricScale:
        value = ScaleDescriptor(
            int("101010101010" * 3, 2), "Whole tone (test)", "symmetric", False
        )

    with pytest.raises(NonFunctionalScaleError):
        is_diatonic(Notes.C, _FakeSymmetricScale, Chord("C"))
