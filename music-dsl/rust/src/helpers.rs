//! `helpers.rs` — bit-primitive operations on scale/encoding integers.
//!
//! Port of `music_dsl/helpers.py` strip_left / strip_right / semitones_apart_ascending.
//! All values are `u64`; Scales.* are ~36-bit, MAX_SUPPORTED is 39-bit.

use crate::notes::Note;

/// 13-bit minimum for scale/encoding operands to strip_left.
pub const MIN_SUPPORTED: u64 = 0b1_0000_0000_0000; // 4096
/// 39-bit maximum (twelve-tone pattern × 3).
pub const MAX_SUPPORTED: u64 = 0b111_1111_1111_111_1111_1111_111_1111_1111_1111_1111; // 549755813887

/// Bit-length of a u64 value (position of the highest set bit + 1).
/// Returns 0 for 0.
#[inline]
pub fn bit_length(v: u64) -> u32 {
    64 - v.leading_zeros()
}

/// Remove `x` high bits from a scale/encoding bit-array.
///
/// Error conditions (matching Python reference):
/// - `bits` outside `[MIN_SUPPORTED, MAX_SUPPORTED]`
/// - `bit_length(bits) < x` (shift would remove more bits than exist)
/// - Fidelity loss: `bit_length(result) != bit_length(bits) - x` (leading-zero after strip)
///
/// When `x == 0`, returns `bits` unchanged (no range check needed per reference).
pub fn strip_left(bits: u64, x: u32) -> Result<u64, &'static str> {
    if x == 0 {
        return Ok(bits);
    }
    if bits < MIN_SUPPORTED || bits > MAX_SUPPORTED {
        return Err("strip_left: bits out of supported range");
    }
    let bl = bit_length(bits);
    if bl < x {
        return Err("strip_left: attempting an invalid shift (x > bit_length)");
    }
    let mask: u64 = (1u64 << (bl - x)) - 1;
    let result = bits & mask;
    if bit_length(result) != bl - x {
        return Err("strip_left: fidelity loss — leading zeros after strip");
    }
    Ok(result)
}

/// Remove `x` low bits from a scale/encoding bit-array (right shift).
///
/// Error condition: `x > bit_length(bits)`.
pub fn strip_right(bits: u64, x: u32) -> Result<u64, &'static str> {
    if x > bit_length(bits) {
        return Err("strip_right: attempting an invalid shift (x > bit_length)");
    }
    Ok(bits >> x)
}

/// Chromatic distance from `root` to `note` ascending within one octave (0–11).
///
/// Mirrors `music_dsl/helpers.py:semitones_apart_ascending`.
/// Uses `Note::chromatic_index()` (same ordering as Python's `TWELVE_TONES`).
pub fn semitones_apart_ascending(root: &str, note: &str) -> i64 {
    let root_note = Note::from_value(root)
        .unwrap_or_else(|| panic!("unknown note: {}", root));
    let note_note = Note::from_value(note)
        .unwrap_or_else(|| panic!("unknown note: {}", note));
    let r = root_note.chromatic_index();
    let n = note_note.chromatic_index();
    (n + 12 - r).rem_euclid(12)
}
