from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.static import Notes, Extensions, Seventh, Triad
from music_dsl.domain.chords.abstract_chord import make_chord_attrs

EXAMPLE_CHORD_STRS = [
    "Ab^7",
    "G7b9",
    "Ab-7",
    "C7b13",
    "E7",
    "D-7",
    "F7",
    "F^7",
    "E^7",
    "D7",
    "A-7",
    "Eb^7",
    "Ch7",
    "C7b9",
    "Bb6",
    "Db7",
    "F#h7",
    "D7b9",
    "C-7",
    "B7b9",
    "G-7",
    "Bo7",
    "Dh7",
    "Bb^7",
    "A7",
    "Gh7",
    "Ab7",
    "Bb-7",
    "Eh7",
    "A7b9",
    "C7",
    "Eb^7#11",
    "F7b9",
    "Db^7",
    "Db-^7",
    "G7b13",
    "G7",
    "F-7",
    "Bb7",
    "Eb7",
    "C^7",
    "Ab7#11",
    "G^7",
    "Gsus4",
]

EXAMPLE_CHORD_ATTRS = [
    make_chord_attrs(Notes("Ab"), Triad.Major, Seventh.Major, [Extensions("")], ""),
    make_chord_attrs(Notes("G"), Triad.Major, Seventh.Minor, [Extensions("b9")], ""),
    make_chord_attrs(Notes("Ab"), Triad.Minor, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("C"), Triad.Major, Seventh.Minor, [Extensions("b13")], ""),
    make_chord_attrs(Notes("E"), Triad.Major, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("D"), Triad.Minor, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("F"), Triad.Major, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("F"), Triad.Major, Seventh.Major, [Extensions("")], ""),
    make_chord_attrs(Notes("E"), Triad.Major, Seventh.Major, [Extensions("")], ""),
    make_chord_attrs(Notes("D"), Triad.Major, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("A"), Triad.Minor, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("Eb"), Triad.Major, Seventh.Major, [Extensions("")], ""),
    make_chord_attrs(
        Notes("C"), Triad.HalfDiminished, Seventh.Minor, [Extensions("")], ""
    ),
    make_chord_attrs(Notes("C"), Triad.Major, Seventh.Minor, [Extensions("b9")], ""),
    make_chord_attrs(Notes("Bb"), Triad.Major, Seventh._None, [Extensions("6")], ""),
    make_chord_attrs(Notes("Db"), Triad.Major, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(
        Notes("F#"), Triad.HalfDiminished, Seventh.Minor, [Extensions("")], ""
    ),
    make_chord_attrs(Notes("D"), Triad.Major, Seventh.Minor, [Extensions("b9")], ""),
    make_chord_attrs(Notes("C"), Triad.Minor, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("B"), Triad.Major, Seventh.Minor, [Extensions("b9")], ""),
    make_chord_attrs(Notes("G"), Triad.Minor, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("B"), Triad.Diminished, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(
        Notes("D"), Triad.HalfDiminished, Seventh.Minor, [Extensions("")], ""
    ),
    make_chord_attrs(Notes("Bb"), Triad.Major, Seventh.Major, [Extensions("")], ""),
    make_chord_attrs(Notes("A"), Triad.Major, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(
        Notes("G"), Triad.HalfDiminished, Seventh.Minor, [Extensions("")], ""
    ),
    make_chord_attrs(Notes("Ab"), Triad.Major, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("Bb"), Triad.Minor, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(
        Notes("E"), Triad.HalfDiminished, Seventh.Minor, [Extensions("")], ""
    ),
    make_chord_attrs(Notes("A"), Triad.Major, Seventh.Minor, [Extensions("b9")], ""),
    make_chord_attrs(Notes("C"), Triad.Major, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("Eb"), Triad.Major, Seventh.Major, [Extensions("#11")], ""),
    make_chord_attrs(Notes("F"), Triad.Major, Seventh.Minor, [Extensions("b9")], ""),
    make_chord_attrs(Notes("Db"), Triad.Major, Seventh.Major, [Extensions("")], ""),
    make_chord_attrs(Notes("Db"), Triad.Minor, Seventh.Major, [Extensions("")], ""),
    make_chord_attrs(Notes("G"), Triad.Major, Seventh.Minor, [Extensions("b13")], ""),
    make_chord_attrs(Notes("G"), Triad.Major, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("F"), Triad.Minor, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("Bb"), Triad.Major, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("Eb"), Triad.Major, Seventh.Minor, [Extensions("")], ""),
    make_chord_attrs(Notes("C"), Triad.Major, Seventh.Major, [Extensions("")], ""),
    make_chord_attrs(Notes("Ab"), Triad.Major, Seventh.Minor, [Extensions("#11")], ""),
    make_chord_attrs(Notes("G"), Triad.Major, Seventh.Major, [Extensions("")], ""),
    make_chord_attrs(Notes("G"), Triad.Sus4, Seventh._None, [Extensions("")], ""),
]

EXAMPLE_CHORDS = zip(EXAMPLE_CHORD_STRS, EXAMPLE_CHORD_ATTRS)
EXAMPLE_ENCODINGS = zip(
    [Chord(str) for str in EXAMPLE_CHORD_STRS],
    (
        int(x or "0", 2)
        for x in (
            "1000100100010000000",  # ^7,
            "1000100100101000000",  # 7b9,
            "1001000100100000000",  # -7
            "1000100100100000010",  # 7b13
            "1000100100100000000",  # "E7"
            "1001000100100000000",  # "D-7"
            "1000100100100000000",  # "F7"
            "",  # "F^7"
            "",  # "E^7"
            "",  # "D7"
            "",  # "A-7"
            "",  # "Eb^7"
            "1001001000100000000",  # "Ch7"
            "",  # "C7b9"
            "1000100101000000000",  # "Bb6"
            "",  # "Db7"
            "",  # "F#h7"
            "",  # "D7b9"
            "",  # "C-7"
            "",  # "B7b9"
            "",  # "G-7"
            "1001001001000000000",  # "Bo7"
            "",  # "Dh7"
            "",  # "Bb^7"
            "",  # "A7"
            "",  # "Gh7"
            "",  # "Ab7"
            "",  # "Bb-7"
            "",  # "Eh7"
            "",  # "A7b9"
            "",  # "C7"
            "1000100100010000100",  # "Eb^7#11"
            "",  # "F7b9"
            "",  # "Db^7"
            "1001000100010000000",  # "Db-^7"
            "",  # "G7b13"
            "",  # "G7"
            "",  # "F-7"
            "",  # "Bb7"
            "",  # "Eb7"
            "",  # "C^7"
            "",  # "Ab7#11"
            "",  # "G^7"
            "1000010100000000000",  # "Gsus4"
        )
    ),
)

DIATONIC_MAJOR_CHORDS = [
    Chord("C^7"),
    Chord("D-7"),
    Chord("E-7"),
    Chord("F^7"),
    Chord("G7"),
    Chord("A7"),
    Chord("Bh7"),
]

ALL_THE_THINGS_YOU_ARE = zip(
    [
        Chord("D-7"),
        Chord("G-7"),
        Chord("C7"),
        Chord("F^7"),
        Chord("Bb^7"),
        Chord("B-7"),
        Chord("E7"),
        Chord("A^7"),
        Chord("A^7"),
    ],
    [
        "vi-7",
        "ii-7",
        "V7",
        "I^7",
        "IV^7",
        "ii-7/III^7",
        "V7/III^7",
        "III^7",
        "III^7",
    ],
)


def generate_all_chord_combinations():
    ...
