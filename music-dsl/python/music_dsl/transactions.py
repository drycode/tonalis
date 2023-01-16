from functools import cache
from typing import List, Union

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.static import (
    TO_C,
    TWELVE_TONES,
    Notes,
    SCALE_DEGREES,
    ScaleDegree,
)
from music_dsl.encode import Scales, strip_left, strip_right
from music_dsl.helpers import get_index, semitones_apart


def normalize_to_c(root: Notes, chords: List[Chord]) -> None:
    semitones = TO_C[root]
    for chord in chords:
        chord.root = modulate(semitones, chord.root)


@cache
def modulate(
    semitones: int, note: Union[Notes, ScaleDegree]
) -> Union[Notes, ScaleDegree]:
    new_idx = (get_index(note) + semitones) % 12
    if isinstance(note, ScaleDegree):
        return SCALE_DEGREES[new_idx].normalize(note.is_flat, note.is_minor)
    return TWELVE_TONES[new_idx]


def _get_key(from_segment: Chord, pattern: "NumericChord"):
    return TWELVE_TONES[
        semitones_apart(from_segment.root.normalized(), pattern.root.normalized())
    ]


def is_diatonic(root: Notes, scale: Scales, chord: Chord):
    """
    Determines if a chord encoding matches the target scale at a particular modal distance from the root
    """

    def get_least_significant_note_position():
        y = chord.encoding - 1
        x = 0
        while y & 1:
            y >>= 1
            x += 1
        return x

    def _root_is_diatonic(scale, scale_length, semitones):
        return scale.value & 1 << (scale_length - semitones - 1)

    semitones = semitones_apart(root, chord.root)
    scale_length = int.bit_length(scale.value)

    # Checks the Nth bit from the left is set, which determines if the root is diatonic to the scale
    if _root_is_diatonic(scale, scale_length, semitones):

        # Pares chord bits down to minimal size of significant notes
        chord_bits = strip_right(chord.encoding, get_least_significant_note_position())

        # Cuts the 3x represented scale down to the size of the modal scale, and aligns it positionally
        # with the appropriate root
        modal_scale = strip_left(scale.value, semitones)

        # Removes superflous bits from the right of the modal scale
        scale_bits = strip_right(
            modal_scale, int.bit_length(modal_scale) - int.bit_length(chord_bits)
        )

        ############ All this needs to be extracted, renamed, and tested ###############
        if chord_bits & scale_bits == chord_bits:
            return True

    return False
