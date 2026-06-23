//! `transactions.rs` — key-relative operations on notes and chords.
//!
//! Port of `music_dsl/transactions.py`: `modulate`, `is_diatonic`,
//! `harmonic_function_in_key`, and `chord_in_key`.

use crate::chord::{chord_encoding, parse_chord, ChordParseError};
use crate::helpers::{semitones_apart_ascending, strip_left, strip_right};
use crate::notes::Note;
use crate::numeric_chord::{parse_numeric, NumericParseError};
use crate::scale_degree::ScaleDegree;
use crate::ChordModel;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// The 12-tone chromatic scale using flat spellings (indices 0–11).
pub static TWELVE_TONES: [&str; 12] = [
    "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B",
];

/// The 12 scale degrees in flat-major form at chromatic positions 0–11.
/// Index 0 = I, 1 = bII, 2 = II, … 11 = VII.
pub static SCALE_DEGREES: [ScaleDegree; 12] = [
    ScaleDegree::I,
    ScaleDegree::BII,
    ScaleDegree::II,
    ScaleDegree::BIII,
    ScaleDegree::III,
    ScaleDegree::IV,
    ScaleDegree::BV,
    ScaleDegree::V,
    ScaleDegree::BVI,
    ScaleDegree::VI,
    ScaleDegree::BVII,
    ScaleDegree::VII,
];

// ---------------------------------------------------------------------------
// modulate
// ---------------------------------------------------------------------------

/// Transpose a note or scale degree by `semitones`.
///
/// If `note` parses as a `ScaleDegree`, the result is the transposed degree
/// preserving flat/minor quality. Otherwise `note` is treated as a `Note`
/// value string and the flat chromatic spelling is returned.
pub fn modulate(semitones: i64, note: &str) -> String {
    // Try ScaleDegree first.
    if let Some(degree) = ScaleDegree::from_value(note) {
        let idx = degree.scale_degree_index();
        let new_idx = (idx + semitones).rem_euclid(12) as usize;
        let base = SCALE_DEGREES[new_idx];
        let is_flat = degree.is_flat();
        let is_minor = degree.is_minor();
        return base.normalize(is_flat, is_minor).value().to_string();
    }
    // Fall through to Note.
    let note_val = Note::from_value(note)
        .unwrap_or_else(|| panic!("modulate: unknown note or scale degree: {:?}", note));
    let idx = note_val.chromatic_index();
    let new_idx = (idx + semitones).rem_euclid(12) as usize;
    TWELVE_TONES[new_idx].to_string()
}

// ---------------------------------------------------------------------------
// is_diatonic
// ---------------------------------------------------------------------------

/// Return true if `chord_str` is diatonic to `root` in the given `scale` value.
///
/// `scale` is the numeric scale value (e.g. from `scale_value("Major")`).
/// Mirrors `music_dsl.transactions.is_diatonic` faithfully.
pub fn is_diatonic(root: &str, scale: u64, chord_str: &str) -> bool {
    // Parse chord root note string — used only to get the root value for the chord model.
    let chord = match parse_chord(chord_str) {
        Ok(m) => m,
        Err(_) => return false,
    };
    let enc = match chord_encoding(chord_str) {
        Ok(v) => v,
        Err(_) => return false,
    };

    // get_least_significant_note_position:
    // count trailing 1-bits of (enc - 1), i.e. trailing zeros of enc.
    let lsb = enc.trailing_zeros();

    // semitones from key root to chord root (ascending)
    let semitones = semitones_apart_ascending(root, &chord.root);

    let scale_length = 64 - scale.leading_zeros(); // bit_length

    // _root_is_diatonic check: is the chord root in the scale?
    let shift = scale_length as i64 - semitones - 1;
    if shift >= 0 && scale & (1u64 << shift as u32) != 0 {
        // chord_bits = strip_right(enc, lsb)
        let chord_bits = match strip_right(enc, lsb) {
            Ok(v) => v,
            Err(_) => return false,
        };
        // modal_scale = strip_left(scale, semitones)
        let modal_scale = match strip_left(scale, semitones as u32) {
            Ok(v) => v,
            Err(_) => return false,
        };
        let chord_bl = 64 - chord_bits.leading_zeros();
        let modal_bl = 64 - modal_scale.leading_zeros();
        if modal_bl >= chord_bl {
            let scale_bits = match strip_right(modal_scale, modal_bl - chord_bl) {
                Ok(v) => v,
                Err(_) => return false,
            };
            if chord_bits & scale_bits == chord_bits {
                return true;
            }
        }
    }
    false
}

// ---------------------------------------------------------------------------
// harmonic_function_in_key
// ---------------------------------------------------------------------------

/// Return the harmonic function name for `chord_str` in the given key.
///
/// For a chord on the root of a minor key that is itself a minor chord,
/// override the generic harmonic function with "Tonic".
/// Otherwise, return the chord's own harmonic function.
pub fn harmonic_function_in_key(key_root: &str, key_is_minor: bool, chord_str: &str) -> String {
    let chord = match parse_chord(chord_str) {
        Ok(m) => m,
        Err(_) => return "Tonic".to_string(),
    };
    let degree = semitones_apart_ascending(key_root, &chord.root);
    if degree == 0 && key_is_minor && chord.triad == "-" {
        return "Tonic".to_string();
    }
    chord.harmonic_function.clone()
}

// ---------------------------------------------------------------------------
// chord_in_key error
// ---------------------------------------------------------------------------

/// Error returned by `chord_in_key`.
#[derive(Debug)]
pub enum ChordInKeyError {
    ParseNumeric(NumericParseError),
    ParseChord(ChordParseError),
}

impl std::fmt::Display for ChordInKeyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ChordInKeyError::ParseNumeric(e) => write!(f, "ChordInKeyError(numeric): {:?}", e),
            ChordInKeyError::ParseChord(e)   => write!(f, "ChordInKeyError(chord): {}", e),
        }
    }
}

// ---------------------------------------------------------------------------
// chord_in_key
// ---------------------------------------------------------------------------

/// Resolve a numeric chord string (e.g. "V7", "V7/V", "ii-7") in a key to an
/// absolute `ChordModel`.
pub fn chord_in_key(numeric_str: &str, key_root: &str) -> Result<ChordModel, ChordInKeyError> {
    let numeric = parse_numeric(numeric_str).map_err(ChordInKeyError::ParseNumeric)?;

    let key_idx = Note::from_value(key_root)
        .unwrap_or_else(|| panic!("chord_in_key: unknown key root {:?}", key_root))
        .chromatic_index();

    // Resolve the absolute root note for the numerator.
    let abs_root: &str = if let Some(denom) = &numeric.denominator {
        // Slash chord: resolve denominator's absolute root first, then resolve numerator within it.
        let denom_deg = ScaleDegree::from_value(&denom.root)
            .unwrap_or_else(|| panic!("chord_in_key: unknown denominator degree {:?}", denom.root));
        let denom_idx = denom_deg.scale_degree_index();
        let denom_abs_idx = (key_idx + denom_idx).rem_euclid(12) as usize;
        let denom_abs_root = TWELVE_TONES[denom_abs_idx];

        let num_deg = ScaleDegree::from_value(&numeric.numerator.root)
            .unwrap_or_else(|| panic!("chord_in_key: unknown numerator degree {:?}", numeric.numerator.root));
        let num_idx = num_deg.scale_degree_index();
        let denom_abs_key_idx = Note::from_value(denom_abs_root)
            .unwrap()
            .chromatic_index();
        let abs_idx = (denom_abs_key_idx + num_idx).rem_euclid(12) as usize;
        TWELVE_TONES[abs_idx]
    } else {
        let num_deg = ScaleDegree::from_value(&numeric.numerator.root)
            .unwrap_or_else(|| panic!("chord_in_key: unknown numerator degree {:?}", numeric.numerator.root));
        let num_idx = num_deg.scale_degree_index();
        let abs_idx = (key_idx + num_idx).rem_euclid(12) as usize;
        TWELVE_TONES[abs_idx]
    };

    // Build the chord string: absolute root + quality suffix from numerator.
    let quality = format!(
        "{}{}{}",
        numeric.numerator.triad,
        numeric.numerator.seventh,
        numeric.numerator.extensions.join("")
    );
    let chord_str = format!("{}{}", abs_root, quality);
    parse_chord(&chord_str).map_err(ChordInKeyError::ParseChord)
}
