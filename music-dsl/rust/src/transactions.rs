//! `transactions.rs` — key-relative operations on notes and chords.
//!
//! Port of `music_dsl/transactions.py`: `modulate`, `is_diatonic`,
//! `harmonic_function_in_key`, and `chord_in_key`.

use crate::chord::{chord_encoding, parse_chord, ChordParseError};
use crate::encode::ScaleDescriptor;
use crate::helpers::{semitones_apart_ascending, strip_left, strip_right};
use crate::notes::Note;
use crate::numeric_chord::{parse_numeric, NumericParseError};
use crate::scale_degree::ScaleDegree;
use crate::ChordModel;

// ---------------------------------------------------------------------------
// Shared error type for transaction functions
// ---------------------------------------------------------------------------

/// Error returned by `modulate`, `is_diatonic`, `harmonic_function_in_key`,
/// and `chord_in_key` on invalid input.
///
/// Matches the Python reference's behaviour: all four functions raise on bad
/// input (unknown note/degree, unparseable chord, unknown key root, etc.).
#[derive(Debug)]
pub enum TransactionError {
    /// The note or scale-degree string was not recognised.
    UnknownNote(String),
    /// The chord string could not be parsed.
    ParseChord(ChordParseError),
    /// A numeric chord string could not be parsed.
    ParseNumeric(NumericParseError),
    /// A scale-degree string (key root, numerator, or denominator) was not recognised.
    UnknownDegree(String),
    /// A functional query (diatonicity / harmonic function) was made against a scale
    /// with no meaningful tonal-function model (whole-tone, diminished, augmented,
    /// chromatic). Tier-1 membership via `encode::contains` still works for these.
    /// Rust counterpart of Python's `NonFunctionalScaleError`.
    NonFunctionalScale(String),
}

impl std::fmt::Display for TransactionError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TransactionError::UnknownNote(s)    => write!(f, "TransactionError: unknown note or scale degree {:?}", s),
            TransactionError::ParseChord(e)     => write!(f, "TransactionError: chord parse error: {}", e),
            TransactionError::ParseNumeric(e)   => write!(f, "TransactionError: numeric parse error: {}", e),
            TransactionError::UnknownDegree(s)  => write!(f, "TransactionError: unknown scale degree {:?}", s),
            TransactionError::NonFunctionalScale(s) => write!(
                f,
                "TransactionError: {} has no diatonic-function model; use encode::contains() for scale membership instead.",
                s
            ),
        }
    }
}

impl std::error::Error for TransactionError {}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

// Domain constants live in their domain modules (notes / scale_degree);
// re-exported here for backward compatibility.
pub use crate::notes::TWELVE_TONES;
pub use crate::scale_degree::SCALE_DEGREES;

// ---------------------------------------------------------------------------
// modulate
// ---------------------------------------------------------------------------

/// Transpose a note or scale degree by `semitones`.
///
/// If `note` parses as a `ScaleDegree`, the result is the transposed degree
/// preserving flat/minor quality. Otherwise `note` is treated as a `Note`
/// value string and the flat chromatic spelling is returned.
///
/// Returns `Err(TransactionError::UnknownNote)` if `note` cannot be parsed as
/// either a `ScaleDegree` or a `Note`. Mirrors the Python reference which raises
/// on unknown input.
pub fn modulate(semitones: i64, note: &str) -> Result<String, TransactionError> {
    // Try ScaleDegree first.
    if let Some(degree) = ScaleDegree::from_value(note) {
        let idx = degree.scale_degree_index();
        let new_idx = (idx + semitones).rem_euclid(12) as usize;
        let base = SCALE_DEGREES[new_idx];
        let is_flat = degree.is_flat();
        let is_minor = degree.is_minor();
        return Ok(base.normalize(is_flat, is_minor).value().to_string());
    }
    // Fall through to Note.
    let note_val = Note::from_value(note)
        .ok_or_else(|| TransactionError::UnknownNote(note.to_string()))?;
    let idx = note_val.chromatic_index();
    let new_idx = (idx + semitones).rem_euclid(12) as usize;
    Ok(TWELVE_TONES[new_idx].to_string())
}

// ---------------------------------------------------------------------------
// is_diatonic
// ---------------------------------------------------------------------------

/// Return `Ok(true)` if `chord_str` is diatonic to `root` in the given `scale`,
/// `Ok(false)` if valid but not diatonic, or `Err` on refusal / bad input.
///
/// `scale` is a [`ScaleDescriptor`] (e.g. from `scale_descriptor("Major")`).
/// Mirrors `music_dsl.transactions.is_diatonic` faithfully:
/// - **Two-tier refusal (Tier 2):** on a non-functional scale (`supports_diatonic_function`
///   is `false` — whole-tone, diminished, augmented, chromatic) it returns
///   `Err(TransactionError::NonFunctionalScale)`. The Python reference raises
///   `NonFunctionalScaleError`; this is the Rust `Result` conversion.
/// - The Python reference raises `InvalidChordStringException` on an unparseable
///   chord string; this returns `Err(TransactionError::ParseChord)` instead.
pub fn is_diatonic(root: &str, scale: &ScaleDescriptor, chord_str: &str) -> Result<bool, TransactionError> {
    // Tier 2 — functional queries are only defined on scales with a tonal
    // hierarchy. Symmetric/atonal scales refuse here; membership lives in
    // `encode::contains`.
    if !scale.supports_diatonic_function {
        return Err(TransactionError::NonFunctionalScale(scale.name.to_string()));
    }
    let scale = scale.mask;
    // ── Algorithm: align the modal window, then mask ──────────────────────────
    //
    // Both a scale and a chord are bit-arrays over semitone slots, MSB = root.
    // A chord is diatonic to a key iff, once rotated so the chord's root lines
    // up with the same slot in the scale, every chord tone falls on a scale
    // tone. This is done in three moves, all on the shared `Scales` ×3 mask so
    // any modal window (root at any of the 12 positions) can be read without a
    // wrap-around:
    //
    //   1. Root-in-scale gate — is the chord's root itself a scale tone? If the
    //      scale bit `semitones` slots below the top is clear, bail early.
    //   2. Align — `strip_left(scale, semitones)` drops the `semitones` high bits,
    //      rotating the scale so its window now *starts* at the chord's root
    //      (the "modal" scale). `strip_right(enc, lsb)` drops the chord encoding's
    //      trailing zero padding so its MSB is the chord root too.
    //   3. Mask — right-trim the aligned scale to the chord's bit-length, then
    //      test `chord_bits & scale_bits == chord_bits`: every set chord bit
    //      must also be set in the scale window. Equality ⇒ diatonic.
    //
    // A `strip_left`/`strip_right` range error (operand outside the supported
    // window) means the chord cannot be diatonic here, so it maps to `Ok(false)`.
    let chord = parse_chord(chord_str).map_err(TransactionError::ParseChord)?;
    let enc = chord_encoding(chord_str).map_err(TransactionError::ParseChord)?;

    // get_least_significant_note_position:
    // count trailing 1-bits of (enc - 1), i.e. trailing zeros of enc.
    let lsb = enc.trailing_zeros();

    // semitones from key root to chord root (ascending)
    let semitones = semitones_apart_ascending(root, &chord.root);

    let scale_length = 64 - scale.leading_zeros(); // bit_length

    // Step 1 — root-in-scale gate: is the chord root a scale tone?
    let shift = scale_length as i64 - semitones - 1;
    if shift >= 0 && scale & (1u64 << shift as u32) != 0 {
        // Step 2 — align chord and scale windows to the chord root.
        let Ok(chord_bits) = strip_right(enc, lsb) else {
            return Ok(false);
        };
        let Ok(modal_scale) = strip_left(scale, semitones as u32) else {
            return Ok(false);
        };
        let chord_bl = 64 - chord_bits.leading_zeros();
        let modal_bl = 64 - modal_scale.leading_zeros();
        // Step 3 — trim the aligned scale to the chord's width, then mask.
        if modal_bl >= chord_bl {
            let Ok(scale_bits) = strip_right(modal_scale, modal_bl - chord_bl) else {
                return Ok(false);
            };
            if chord_bits & scale_bits == chord_bits {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

// ---------------------------------------------------------------------------
// harmonic_function_in_key
// ---------------------------------------------------------------------------

/// Return the harmonic function name for `chord_str` in the given key,
/// or `Err` if `chord_str` cannot be parsed.
///
/// For a chord on the root of a minor key that is itself a minor chord,
/// override the generic harmonic function with `"Tonic"`.
/// Otherwise, return the chord's own harmonic function.
///
/// Mirrors the Python reference which raises `InvalidChordStringException` on an
/// unparseable chord; this returns `Err(TransactionError::ParseChord)` instead.
/// A legitimate `"Tonic"` classification is returned as `Ok("Tonic".to_string())`.
pub fn harmonic_function_in_key(key_root: &str, key_is_minor: bool, chord_str: &str) -> Result<String, TransactionError> {
    let chord = parse_chord(chord_str).map_err(TransactionError::ParseChord)?;
    let degree = semitones_apart_ascending(key_root, &chord.root);
    if degree == 0 && key_is_minor && chord.triad == "-" {
        return Ok("Tonic".to_string());
    }
    Ok(chord.harmonic_function.clone())
}

// ---------------------------------------------------------------------------
// chord_in_key
// ---------------------------------------------------------------------------

/// Resolve a numeric chord string (e.g. "V7", "V7/V", "ii-7") in a key to an
/// absolute `ChordModel`.
///
/// Returns `Err(TransactionError)` on:
/// - Unparseable numeric string
/// - Unknown key root note
/// - Unknown numerator or denominator scale degree
/// - Unparseable resulting absolute chord string
pub fn chord_in_key(numeric_str: &str, key_root: &str) -> Result<ChordModel, TransactionError> {
    let numeric = parse_numeric(numeric_str).map_err(TransactionError::ParseNumeric)?;

    let key_idx = Note::from_value(key_root)
        .ok_or_else(|| TransactionError::UnknownNote(key_root.to_string()))?
        .chromatic_index();

    // Resolve the absolute root note for the numerator.
    let abs_root: &str = if let Some(denom) = &numeric.denominator {
        // Slash chord: resolve denominator's absolute root first, then resolve numerator within it.
        let denom_deg = ScaleDegree::from_value(&denom.root)
            .ok_or_else(|| TransactionError::UnknownDegree(denom.root.clone()))?;
        let denom_idx = denom_deg.scale_degree_index();
        let denom_abs_idx = (key_idx + denom_idx).rem_euclid(12) as usize;
        let denom_abs_root = TWELVE_TONES[denom_abs_idx];

        let num_deg = ScaleDegree::from_value(&numeric.numerator.root)
            .ok_or_else(|| TransactionError::UnknownDegree(numeric.numerator.root.clone()))?;
        let num_idx = num_deg.scale_degree_index();
        // denom_abs_root is always a valid TWELVE_TONES entry — this unwrap is safe.
        let denom_abs_key_idx = Note::from_value(denom_abs_root)
            .ok_or_else(|| TransactionError::UnknownNote(denom_abs_root.to_string()))?
            .chromatic_index();
        let abs_idx = (denom_abs_key_idx + num_idx).rem_euclid(12) as usize;
        TWELVE_TONES[abs_idx]
    } else {
        let num_deg = ScaleDegree::from_value(&numeric.numerator.root)
            .ok_or_else(|| TransactionError::UnknownDegree(numeric.numerator.root.clone()))?;
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
    parse_chord(&chord_str).map_err(TransactionError::ParseChord)
}
