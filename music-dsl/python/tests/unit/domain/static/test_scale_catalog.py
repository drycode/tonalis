"""DRY-412: exhaustive scale catalog — correctness of every pitch-class set.

Each scale's `contains` membership is asserted against its canonical pitch-class
set (semitones above the tonic). This verifies `_scale_mask` + `contains` for
5-, 6-, 7-, 8- and 12-note scales, and documents exactly what was blessed.
"""

from music_dsl.encode import Scales, contains

# Canonical pitch-class sets (semitones from tonic). Source of truth for the catalog.
EXPECTED = {
    # major modes
    "Major": {0, 2, 4, 5, 7, 9, 11},
    "Dorian": {0, 2, 3, 5, 7, 9, 10},
    "Phrygian": {0, 1, 3, 5, 7, 8, 10},
    "Lydian": {0, 2, 4, 6, 7, 9, 11},
    "Mixolydian": {0, 2, 4, 5, 7, 9, 10},
    "Minor": {0, 2, 3, 5, 7, 8, 10},
    "Locrian": {0, 1, 3, 5, 6, 8, 10},
    # melodic minor modes
    "MelodicMinor": {0, 2, 3, 5, 7, 9, 11},
    "DorianFlat2": {0, 1, 3, 5, 7, 9, 10},
    "LydianAugmented": {0, 2, 4, 6, 8, 9, 11},
    "LydianDominant": {0, 2, 4, 6, 7, 9, 10},
    "MixolydianFlat6": {0, 2, 4, 5, 7, 8, 10},
    "LocrianNatural2": {0, 2, 3, 5, 6, 8, 10},
    "Altered": {0, 1, 3, 4, 6, 8, 10},
    # harmonic minor modes
    "HarmonicMinor": {0, 2, 3, 5, 7, 8, 11},
    "LocrianNatural6": {0, 1, 3, 5, 6, 9, 10},
    "IonianSharp5": {0, 2, 4, 5, 8, 9, 11},
    "DorianSharp4": {0, 2, 3, 6, 7, 9, 10},
    "PhrygianDominant": {0, 1, 4, 5, 7, 8, 10},
    "LydianSharp2": {0, 3, 4, 6, 7, 9, 11},
    "Ultralocrian": {0, 1, 3, 4, 6, 8, 9},
    # harmonic major + exotics
    "HarmonicMajor": {0, 2, 4, 5, 7, 8, 11},
    "DoubleHarmonic": {0, 1, 4, 5, 7, 8, 11},
    "HungarianMinor": {0, 2, 3, 6, 7, 8, 11},
    "HungarianMajor": {0, 3, 4, 6, 7, 9, 10},
    "NeapolitanMajor": {0, 1, 3, 5, 7, 9, 11},
    "NeapolitanMinor": {0, 1, 3, 5, 7, 8, 11},
    # pentatonic + blues
    "MajorPentatonic": {0, 2, 4, 7, 9},
    "MinorPentatonic": {0, 3, 5, 7, 10},
    "Blues": {0, 3, 5, 6, 7, 10},
    # bebop
    "BebopDominant": {0, 2, 4, 5, 7, 9, 10, 11},
    "BebopMajor": {0, 2, 4, 5, 7, 8, 9, 11},
    # symmetric / atonal
    "WholeTone": {0, 2, 4, 6, 8, 10},
    "DiminishedHalfWhole": {0, 1, 3, 4, 6, 7, 9, 10},
    "DiminishedWholeHalf": {0, 2, 3, 5, 6, 8, 9, 11},
    "Augmented": {0, 3, 4, 7, 8, 11},
    "Chromatic": set(range(12)),
}

NON_FUNCTIONAL = {
    "WholeTone", "DiminishedHalfWhole", "DiminishedWholeHalf", "Augmented", "Chromatic",
}


def test_every_scale_has_expected_membership():
    for scale in Scales:
        expected = EXPECTED[scale.name]
        actual = {pc for pc in range(12) if contains(scale, pc)}
        assert actual == expected, f"{scale.name}: {actual} != {expected}"


def test_catalog_is_complete_and_no_extras():
    assert {s.name for s in Scales} == set(EXPECTED)


def test_functional_flags():
    for scale in Scales:
        want_functional = scale.name not in NON_FUNCTIONAL
        assert scale.value.supports_diatonic_function is want_functional, scale.name


def test_legacy_masks_unchanged():
    # The three original scales must keep their exact 36-bit masks (byte-identical
    # conformance contract).
    assert Scales.Major.value.mask == int("101011010101" * 3, 2)
    assert Scales.Minor.value.mask == int("101101011010" * 3, 2)
    assert Scales.HarmonicMinor.value.mask == int("101101011001" * 3, 2)


def test_every_scale_contains_its_tonic():
    for scale in Scales:
        assert contains(scale, 0), scale.name
