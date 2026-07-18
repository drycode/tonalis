from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, Union

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.static import (
    TWELVE_TONES,
    HarmonicFunctions,
    Notes,
    SCALE_DEGREES,
    ScaleDegree,
    Triad,
)
from music_dsl.encode import NonFunctionalScaleError, Scales, strip_left, strip_right
from music_dsl.helpers import get_index, semitones_apart_ascending

if TYPE_CHECKING:
    from music_dsl.domain.chords.numeric_chord import NumericChord


@cache
def modulate(
    semitones: int, note: Union[Notes, ScaleDegree]
) -> Union[Notes, ScaleDegree]:
    new_idx = (get_index(note) + semitones) % 12
    if isinstance(note, ScaleDegree):
        return SCALE_DEGREES[new_idx].normalize(note.is_flat, note.is_minor)
    return TWELVE_TONES[new_idx]


def harmonic_function_in_key(
    key_root: Notes, key_is_minor: bool, chord: Chord
) -> HarmonicFunctions:
    """Determine a chord's harmonic function *relative to a key center*.

    The bare `Chord.harmonic_function` is decided from quality alone and is
    key-agnostic, so it cannot tell a minor tonic (`i-7`) from a `ii-7` — both
    are minor-7 chords and both come back as Subdominant. That mislabels the
    tonic of every minor key.

    This function layers the one key-dependent rule the quality-only mapping
    cannot express: a chord built on the *tonic scale degree* is Tonic,
    regardless of its quality. In a minor key the tonic is a `-7` (would
    otherwise read Subdominant); in a major key the tonic is already Tonic, so
    this is a no-op there. A dominant-quality chord on the tonic degree (a blues
    `I7`) is left as-is so it can still be labeled `I7`.

    Everything else falls back to the existing quality-based classification, so
    major-key behavior is unchanged.
    """
    degree = semitones_apart_ascending(key_root, chord.root)
    if degree == 0:
        # The tonic-degree minor-7 chord (the i-7 of a minor key) functions as
        # Tonic. Major/dominant/dim tonic-degree chords keep their quality-based
        # function so blues I7 and the like are unaffected.
        if key_is_minor and chord.triad == Triad.Minor:
            return HarmonicFunctions.Tonic
    return chord.harmonic_function


def _get_key(from_segment: Chord, pattern: "NumericChord"):
    return TWELVE_TONES[
        semitones_apart_ascending(
            from_segment.root.normalized(), pattern.root.normalized()
        )
    ]


def is_diatonic(root: Notes, scale: Scales, chord: Chord):
    """
    Determines if a chord encoding matches the target scale at a particular modal distance from the root
    """
    # Two-tier model: functional queries are only defined on scales with a tonal
    # hierarchy. Symmetric/atonal scales refuse here; membership lives in contains().
    if not scale.value.supports_diatonic_function:
        raise NonFunctionalScaleError(
            f"{scale.value.name} has no diatonic-function model; "
            "use encode.contains() for scale membership instead."
        )

    def get_least_significant_note_position():
        y = chord.encoding - 1
        x = 0
        while y & 1:
            y >>= 1
            x += 1
        return x

    def _root_is_diatonic(scale, scale_length, semitones):
        return scale.value.mask & 1 << (scale_length - semitones - 1)

    semitones = semitones_apart_ascending(root, chord.root)
    scale_length = int.bit_length(scale.value.mask)

    # Checks the Nth bit from the left is set, which determines if the root is diatonic to the scale
    if _root_is_diatonic(scale, scale_length, semitones):

        # Pares chord bits down to minimal size of significant notes
        chord_bits = strip_right(chord.encoding, get_least_significant_note_position())

        # Cuts the 3x represented scale down to the size of the modal scale, and aligns it positionally
        # with the appropriate root
        modal_scale = strip_left(scale.value.mask, semitones)

        # Removes superflous bits from the right of the modal scale
        scale_bits = strip_right(
            modal_scale, int.bit_length(modal_scale) - int.bit_length(chord_bits)
        )

        # Diatonic iff the chord's significant bits are a subset of the aligned modal scale.
        if chord_bits & scale_bits == chord_bits:
            return True

    return False


def _quality_suffix(numeric) -> str:
    """Chord-parseable suffix from the numeric chord's enum values (NOT repr)."""
    triad = numeric.triad.value
    seventh = numeric._7th.value
    exts = "".join(e.value for e in (numeric.extensions or ()))
    return triad + seventh + exts


def chord_in_key(numeric: "NumericChord", key_root: Notes) -> Chord:
    """Realize a key-relative NumericChord into a playable absolute Chord by
    PITCH CLASS. Flat-spelled (Notes has no double-accidentals); exact for the
    realized pitches. Slash chords resolve recursively against major parents."""
    if numeric.denominator:
        denom_root = modulate(get_index(numeric.denominator.root), key_root)
        abs_root = modulate(get_index(numeric.root), denom_root)
    else:
        abs_root = modulate(get_index(numeric.root), key_root)
    return Chord(abs_root.value + _quality_suffix(numeric))
