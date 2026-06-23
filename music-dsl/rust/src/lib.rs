//! MusicDSL — music-theory domain (notes, intervals, scale-degrees, chords, encoding).
//!
//! Port of the Python `music_dsl` reference for the tonalis / HarmonicAnalyzer project.
//! Build 1 scope: static domain only — Notes, Intervals, ScaleDegree, chord-quality enums,
//! and the five conformance-op public functions.
//! Build 2 scope: encode layer — EncodingMap, Scales, strip ops, semitones_apart_ascending.
//!
//! Public enums use `#[derive(PartialEq, Eq)]` for **structural** equality.
//! Enharmonic / pitch-class equality is in the explicit `notes_equal` / `scale_degrees_equal`
//! functions below — it is NEVER encoded in `PartialEq`.

pub mod chord;
pub mod chord_quality;
pub mod encode;
pub mod get_index;
pub mod helpers;
pub mod notes;
pub mod numeric_chord;
pub mod scale_degree;
pub mod transactions;

pub use chord::{chord_encoding, parse_chord, ChordModel, ChordModelWrapper, ChordParseError};
pub use chord_quality::{Extensions, HarmonicFunction, Seventh, Triad};
pub use encode::{
    encoding_value, encoding_value_from_enums, scale_value,
    CHORD_ENCODING_BIT_LENGTH, DIMINISHED_ENCODING, EMPTY_CHORD_ENCODING,
};
pub use helpers::{semitones_apart_ascending, strip_left, strip_right};
pub use notes::Note;
pub use numeric_chord::{numeric_from_chord, parse_numeric, NumericChordAttrs, NumericChordModel, NumericParseError};
pub use scale_degree::ScaleDegree;
pub use transactions::{chord_in_key, harmonic_function_in_key, is_diatonic, modulate, TWELVE_TONES};

// ---------------------------------------------------------------------------
// Intervals (13-member int enum, structural ==)
// ---------------------------------------------------------------------------

/// Interval — semitone distance, 0 (Unison) through 12 (Octave).
/// Looked up by **member name** (`"m6"`, `"Octave"`, …), not by value.
/// `==` is structural (derived): `Min6 != Maj3`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Interval {
    Unison  = 0,
    Min2    = 1,
    Maj2    = 2,
    Min3    = 3,
    Maj3    = 4,
    P4      = 5,
    Tritone = 6,
    P5      = 7,
    Min6    = 8,
    Maj6    = 9,
    Min7    = 10,
    Maj7    = 11,
    Octave  = 12,
}

impl Interval {
    /// Parse by the canonical member name string (`"m6"`, `"M3"`, `"Tritone"`, …).
    pub fn from_name(name: &str) -> Option<Self> {
        match name {
            "Unison"  => Some(Interval::Unison),
            "m2"      => Some(Interval::Min2),
            "M2"      => Some(Interval::Maj2),
            "m3"      => Some(Interval::Min3),
            "M3"      => Some(Interval::Maj3),
            "P4"      => Some(Interval::P4),
            "Tritone" => Some(Interval::Tritone),
            "P5"      => Some(Interval::P5),
            "m6"      => Some(Interval::Min6),
            "M6"      => Some(Interval::Maj6),
            "m7"      => Some(Interval::Min7),
            "M7"      => Some(Interval::Maj7),
            "Octave"  => Some(Interval::Octave),
            _         => None,
        }
    }

    /// Semitone count (the integer value of the interval).
    pub fn semitones(self) -> i64 {
        self as i64
    }

    /// Up direction (positive semitones).
    pub fn up(self) -> i64 { self.semitones() }

    /// Down direction (negative semitones).
    pub fn down(self) -> i64 { -self.semitones() }
}

// ---------------------------------------------------------------------------
// Public conformance-op functions
// ---------------------------------------------------------------------------

/// `intervals_equal(a, b)` — structural equality on the parsed `Interval` members.
/// Both args are member names (e.g. `"m6"`, `"Octave"`).
pub fn intervals_equal(a: &str, b: &str) -> bool {
    let ia = Interval::from_name(a).unwrap_or_else(|| panic!("unknown interval name: {}", a));
    let ib = Interval::from_name(b).unwrap_or_else(|| panic!("unknown interval name: {}", b));
    ia == ib
}

/// `interval_semitones(name)` — semitone count for the named interval.
pub fn interval_semitones(name: &str) -> i64 {
    Interval::from_name(name)
        .unwrap_or_else(|| panic!("unknown interval name: {}", name))
        .semitones()
}

/// `notes_equal(a, b)` — enharmonic equality: true iff same pitch class.
/// Inputs are note value strings (e.g. `"C#"`, `"Db"`).
pub fn notes_equal(a: &str, b: &str) -> bool {
    let na = Note::from_value(a).unwrap_or_else(|| panic!("unknown note: {}", a));
    let nb = Note::from_value(b).unwrap_or_else(|| panic!("unknown note: {}", b));
    // Enharmonic equality: same pitch class iff same chromatic index.
    na.chromatic_index() == nb.chromatic_index()
}

/// `note_index(value)` — chromatic index 0–11 of a note value string.
pub fn note_index(value: &str) -> i64 {
    Note::from_value(value)
        .unwrap_or_else(|| panic!("unknown note: {}", value))
        .chromatic_index()
}

/// `scale_degrees_equal(a, b)` — enharmonic equality over `sharps_to_flats`/`flats_to_sharps`.
/// Major/minor stay distinct: `"II" != "ii"`.
/// Inputs are scale degree value strings (e.g. `"#iv"`, `"bv"`, `"ii"`).
pub fn scale_degrees_equal(a: &str, b: &str) -> bool {
    let da = ScaleDegree::from_value(a).unwrap_or_else(|| panic!("unknown scale degree: {}", a));
    let db = ScaleDegree::from_value(b).unwrap_or_else(|| panic!("unknown scale degree: {}", b));
    // Enharmonic equality: normalize each to (major, flat) form.
    // Major/minor distinction is preserved because to_flat() does NOT strip case —
    // it only converts # → b within the same case family.
    // We need to compare enharmonics while preserving major/minor.
    // Strategy: both sharps and flats of the same pitch-class (same case) collapse to the
    // same flat degree via to_flat(). Minor degrees can only be enharmonic to other minor
    // degrees and major to major (the sharps_to_flats table is case-consistent).
    da.to_flat() == db.to_flat()
}
