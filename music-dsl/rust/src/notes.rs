//! Notes — the 17-spelling chromatic pitch set (C, C#, Db, … B).
//! `==` is structural (derived). Enharmonic equality is `notes_equal()` in lib.rs.

/// The 17 spelled note values.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Note {
    C,
    Cs,
    Db,
    D,
    Ds,
    Eb,
    E,
    F,
    Fs,
    Gb,
    G,
    Gs,
    Ab,
    A,
    As,
    Bb,
    B,
}

impl Note {
    /// Parse a note from its display value string (e.g. `"C#"`, `"Db"`, `"A"`).
    pub fn from_value(s: &str) -> Option<Self> {
        match s {
            "C"  => Some(Note::C),
            "C#" => Some(Note::Cs),
            "Db" => Some(Note::Db),
            "D"  => Some(Note::D),
            "D#" => Some(Note::Ds),
            "Eb" => Some(Note::Eb),
            "E"  => Some(Note::E),
            "F"  => Some(Note::F),
            "F#" => Some(Note::Fs),
            "Gb" => Some(Note::Gb),
            "G"  => Some(Note::G),
            "G#" => Some(Note::Gs),
            "Ab" => Some(Note::Ab),
            "A"  => Some(Note::A),
            "A#" => Some(Note::As),
            "Bb" => Some(Note::Bb),
            "B"  => Some(Note::B),
            _    => None,
        }
    }

    /// Display value string (the canonical chord-spelling).
    pub fn value(self) -> &'static str {
        match self {
            Note::C  => "C",
            Note::Cs => "C#",
            Note::Db => "Db",
            Note::D  => "D",
            Note::Ds => "D#",
            Note::Eb => "Eb",
            Note::E  => "E",
            Note::F  => "F",
            Note::Fs => "F#",
            Note::Gb => "Gb",
            Note::G  => "G",
            Note::Gs => "G#",
            Note::Ab => "Ab",
            Note::A  => "A",
            Note::As => "A#",
            Note::Bb => "Bb",
            Note::B  => "B",
        }
    }

    /// Normalize to the flat spelling (sharps → flat equivalent; natural/flat → self).
    pub fn to_flat(self) -> Self {
        match self {
            Note::Cs => Note::Db,
            Note::Ds => Note::Eb,
            Note::Fs => Note::Gb,
            Note::Gs => Note::Ab,
            Note::As => Note::Bb,
            other    => other,
        }
    }

    /// Chromatic index 0–11 in the TWELVE_TONES flat ordering.
    pub fn chromatic_index(self) -> i64 {
        match self {
            Note::C  => 0,
            Note::Cs => 1,
            Note::Db => 1,
            Note::D  => 2,
            Note::Ds => 3,
            Note::Eb => 3,
            Note::E  => 4,
            Note::F  => 5,
            Note::Fs => 6,
            Note::Gb => 6,
            Note::G  => 7,
            Note::Gs => 8,
            Note::Ab => 8,
            Note::A  => 9,
            Note::As => 10,
            Note::Bb => 10,
            Note::B  => 11,
        }
    }
}

/// The 12-tone chromatic scale using flat spellings (indices 0-11).
pub static TWELVE_TONES: [&str; 12] = [
    "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B",
];
