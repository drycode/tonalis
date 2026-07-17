from music_dsl.utils import JsonSerializableEnum

# Enharmonic spelling maps, keyed by note string value. Defined at module level
# (NOT inside the Enum body) so they don't become Notes members — a dict assigned
# in an Enum class body is turned into a member and pollutes iteration/len.
_SHARPS_TO_FLATS = {"C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb"}
_FLATS_TO_SHARPS = {flat: sharp for sharp, flat in _SHARPS_TO_FLATS.items()}


class Notes(JsonSerializableEnum):
    C = "C"
    Cs = "C#"
    Db = "Db"
    D = "D"
    Ds = "D#"
    Eb = "Eb"
    E = "E"
    F = "F"
    Fs = "F#"
    Gb = "Gb"
    G = "G"
    Gs = "G#"
    Ab = "Ab"
    A = "A"
    As = "A#"
    Bb = "Bb"
    B = "B"

    def to_flat(self):
        if self.value not in _SHARPS_TO_FLATS:
            return self
        return Notes(_SHARPS_TO_FLATS[self.value])

    def normalized(self):
        return self.to_flat()

    def __eq__(self, other):
        enharmonic = _SHARPS_TO_FLATS.get(other.value) or _FLATS_TO_SHARPS.get(
            other.value
        )
        return self.value == other.value or self.value == enharmonic

    def __hash__(self):
        # Consistent with the enharmonic __eq__: sharps/flats of the same pitch
        # (Cs/Db, ...) normalize to one flat spelling, so equal notes hash equal.
        return hash(self.to_flat().value)

    @classmethod
    def names_by_value(cls):
        """Map each note's string value to its member name (e.g. ``'C#' -> 'Cs'``)."""
        return {note.value: note.name for note in cls}


TO_C = {
    Notes.C: 0,
    Notes.Cs: 1,
    Notes.Db: 1,
    Notes.D: 2,
    Notes.Ds: 3,
    Notes.Eb: 3,
    Notes.E: 4,
    Notes.F: 5,
    Notes.Fs: 6,
    Notes.Gb: 6,
    Notes.G: 7,
    Notes.Gs: 8,
    Notes.Ab: 8,
    Notes.A: 9,
    Notes.As: 10,
    Notes.Bb: 10,
    Notes.B: 11,
}

TWELVE_TONES = [
    Notes.C,
    Notes.Db,
    Notes.D,
    Notes.Eb,
    Notes.E,
    Notes.F,
    Notes.Gb,
    Notes.G,
    Notes.Ab,
    Notes.A,
    Notes.Bb,
    Notes.B,
]


class Intervals(int, JsonSerializableEnum):
    Unison = 0
    m2 = 1
    M2 = 2
    m3 = 3
    M3 = 4
    P4 = 5
    Tritone = 6
    P5 = 7
    m6 = 8
    M6 = 9
    m7 = 10
    M7 = 11
    Octave = 12

    def up(self):
        return self.value

    def down(self):
        return -self.value

