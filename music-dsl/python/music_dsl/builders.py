from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.numeric_chord import NumericChord
from music_dsl.domain.static import Extensions, Notes, Seventh, Triad


def build_chord(root: Notes, triad: Triad, _7th: Seventh, extensions: Extensions):
    return Chord.from_attrs(root, triad, _7th, extensions)


def build_from_chord_string(chord_str: str, parser_type=Chord):
    if parser_type == Chord:
        return Chord(chord_str)
    elif parser_type == NumericChord:
        return NumericChord.from_chord_string(chord_str)
    raise Exception


# TODO: need a more sophisticated wrapper around the ChordAttrs tuple; a builder to prevent illegal
#   attrs such as I^76/I and I-^7/I
