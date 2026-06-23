from music_dsl.utils import JsonSerializableEnum


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

    sharps_to_flats = {
        Cs: Db,
        Ds: Eb,
        Fs: Gb,
        Gs: Ab,
        As: Bb,
    }

    flats_to_sharps = {
        Db: Cs,
        Eb: Ds,
        Gb: Fs,
        Ab: Gs,
        Bb: As,
    }

    def to_flat(self):
        if self.value not in Notes.sharps_to_flats.value:
            return self
        return Notes(Notes.sharps_to_flats.value[self.value])

    def normalized(self):
        return self.to_flat()

    def __eq__(self, other):
        enharmonic = Notes.sharps_to_flats.value.get(
            other.value
        ) or Notes.flats_to_sharps.value.get(other.value)
        return self.value == other.value or self.value == enharmonic

    def __hash__(self):
        return hash(Notes.sharps_to_flats.value.get(self.name) or self.name)

    def __dict__(self):
        return {
            note.value: note.name
            for note in [
                Notes.C,
                Notes.Cs,
                Notes.Db,
                Notes.D,
                Notes.Ds,
                Notes.Eb,
                Notes.E,
                Notes.F,
                Notes.Fs,
                Notes.Gb,
                Notes.G,
                Notes.Gs,
                Notes.Ab,
                Notes.A,
                Notes.As,
                Notes.Bb,
                Notes.B,
            ]
        }


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

