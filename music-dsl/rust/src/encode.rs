//! `encode.rs` — chord encoding + scale constants.
//!
//! Port of `music_dsl/encode.py` (Encoding, EncodingMap, Scales, scan_scale).
//! All integers are `u64`; `Scales.*` are ~36-bit, chord encodings ≤19 bits.
//! `scan_scale` is NOT implemented (dropped — dead+broken in reference).

use crate::chord_quality::{Extensions, Seventh, Triad};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Sentinel bit for chord encodings. Bit 18 set. `0b1000000000000000000 = 262144`.
pub const EMPTY_CHORD_ENCODING: u64 = 1 << 18; // 262144

/// Bit length of the chord encoding window.
pub const CHORD_ENCODING_BIT_LENGTH: u32 = 19;

/// Special-cased fully-diminished chord encoding. `0b1001001001000000000 = 299520`.
pub const DIMINISHED_ENCODING: u64 = 0b1001001001000000000;

// ---------------------------------------------------------------------------
// Scale constants (36-bit, twelve-tone pattern × 3)
// ---------------------------------------------------------------------------

/// Scales (36-bit integers, modal alignment via ×3 pattern).
pub struct Scales;

impl Scales {
    pub const MAJOR: u64 = 46534580949;          // int("101011010101" * 3, 2)
    pub const MINOR: u64 = 48766495578;          // int("101101011010" * 3, 2)
    pub const HARMONIC_MINOR: u64 = 48749714265; // int("101101011001" * 3, 2)
}

/// Return the numeric scale value by name (`"Major"`, `"Minor"`, `"HarmonicMinor"`).
pub fn scale_value(name: &str) -> u64 {
    match name {
        "Major"         => Scales::MAJOR,
        "Minor"         => Scales::MINOR,
        "HarmonicMinor" => Scales::HARMONIC_MINOR,
        other           => panic!("unknown scale name: {}", other),
    }
}

// ---------------------------------------------------------------------------
// EncodingMap — enum member → semitone bit positions
// ---------------------------------------------------------------------------

/// Semitone bit positions for a Triad variant.
fn triad_bits(t: Triad) -> &'static [u32] {
    match t {
        Triad::Major          => &[4, 7],
        Triad::Minor          => &[3, 7],
        Triad::Diminished     => &[3, 6],
        Triad::HalfDiminished => &[3, 6],
        Triad::Augmented      => &[4, 8],
        Triad::Sus2           => &[2, 7],
        Triad::Sus            => &[5, 7],
        Triad::Sus4           => &[5, 7],
    }
}

/// Semitone bit positions for a Seventh variant.
fn seventh_bits(s: Seventh) -> &'static [u32] {
    match s {
        Seventh::Minor => &[10],
        Seventh::Major => &[11],
        Seventh::None  => &[],
    }
}

/// Semitone bit positions for an Extensions variant.
fn extension_bits(e: Extensions) -> &'static [u32] {
    match e {
        Extensions::None   => &[],
        Extensions::Add2   => &[2],
        Extensions::Add3   => &[4],
        Extensions::B5     => &[6],
        Extensions::Add5   => &[7],
        Extensions::S5     => &[8],
        Extensions::B6     => &[8],
        Extensions::Add6   => &[9],
        Extensions::B9     => &[12],
        Extensions::Add9   => &[13],
        Extensions::S9     => &[14],
        Extensions::Add11  => &[15],
        Extensions::S11    => &[16],
        Extensions::B13    => &[17],
        Extensions::Add13  => &[18],
        Extensions::Alt    => &[12, 14, 16, 17],
    }
}

// ---------------------------------------------------------------------------
// Internal encode primitive
// ---------------------------------------------------------------------------

/// Encode a list of semitone positions into a 19-bit integer.
///
/// Empty input → 0. Otherwise, start from EMPTY_CHORD_ENCODING and for each
/// shift `s` set bit `CHORD_ENCODING_BIT_LENGTH - (s + 1)` = bit `18 - s`.
fn encode(bit_positions: &[u32]) -> u64 {
    if bit_positions.is_empty() {
        return 0;
    }
    let mut enc = EMPTY_CHORD_ENCODING;
    for &shift in bit_positions {
        enc |= 1u64 << (CHORD_ENCODING_BIT_LENGTH - (shift + 1));
    }
    enc
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/// Parse an Extensions name string (conformance args use member names).
///
/// Member names follow the Python reference enum member names.
fn extension_from_name(name: &str) -> Extensions {
    match name {
        "add2"  => Extensions::Add2,
        "add3"  => Extensions::Add3,
        "b5"    => Extensions::B5,
        "add5"  => Extensions::Add5,
        "s5"    => Extensions::S5,
        "b6"    => Extensions::B6,
        "add6"  => Extensions::Add6,
        "b9"    => Extensions::B9,
        "add9"  => Extensions::Add9,
        "s9"    => Extensions::S9,
        "add11" => Extensions::Add11,
        "s11"   => Extensions::S11,
        "b13"   => Extensions::B13,
        "add13" => Extensions::Add13,
        "alt"   => Extensions::Alt,
        other   => panic!("unknown extension name: {}", other),
    }
}

/// Parse a Triad from its Python enum member name.
fn triad_from_name(name: &str) -> Triad {
    match name {
        "Major"          => Triad::Major,
        "Minor"          => Triad::Minor,
        "Diminished"     => Triad::Diminished,
        "HalfDiminished" => Triad::HalfDiminished,
        "Augmented"      => Triad::Augmented,
        "Sus"            => Triad::Sus,
        "Sus2"           => Triad::Sus2,
        "Sus4"           => Triad::Sus4,
        other            => panic!("unknown triad name: {}", other),
    }
}

/// Parse a Seventh from its Python enum member name.
fn seventh_from_name(name: &str) -> Seventh {
    match name {
        "Major" => Seventh::Major,
        "Minor" => Seventh::Minor,
        // Python reference uses `_None`; also accept `None` defensively.
        "_None" | "None" => Seventh::None,
        other => panic!("unknown seventh name: {}", other),
    }
}

/// Compute `Encoding.value` from named parts.
///
/// Mirrors `Encoding.__init__` + `.value` property:
/// - `Diminished` triad → `DIMINISHED_ENCODING` (ignoring seventh, extensions)
/// - Otherwise: `core = encode(triad_bits ++ seventh_bits)`, `exts = encode(concat(ext_bits))`,
///   return `core | exts`.
///
/// `root` and `contextual_tonic` are irrelevant to the integer value (fixed to `Notes.C`/`None`).
pub fn encoding_value(triad: &str, seventh: &str, extensions: &[&str]) -> u64 {
    let t = triad_from_name(triad);
    let s = seventh_from_name(seventh);

    let core = if t == Triad::Diminished {
        DIMINISHED_ENCODING
    } else {
        // Concatenate triad + seventh bit positions
        let mut positions: Vec<u32> = Vec::new();
        positions.extend_from_slice(triad_bits(t));
        positions.extend_from_slice(seventh_bits(s));
        encode(&positions)
    };

    // Accumulate all extension bits
    let mut ext_positions: Vec<u32> = Vec::new();
    for &ext_name in extensions {
        let ext = extension_from_name(ext_name);
        ext_positions.extend_from_slice(extension_bits(ext));
    }
    let exts = encode(&ext_positions);

    core | exts
}

/// Compute `Encoding.value` directly from enum types (avoids value→name round-trip).
///
/// Same logic as `encoding_value` but takes enum variants directly so callers
/// that already hold parsed enums don't need to convert back to name strings.
pub fn encoding_value_from_enums(triad: Triad, seventh: Seventh, extensions: &[Extensions]) -> u64 {
    let core = if triad == Triad::Diminished {
        DIMINISHED_ENCODING
    } else {
        let mut positions: Vec<u32> = Vec::new();
        positions.extend_from_slice(triad_bits(triad));
        positions.extend_from_slice(seventh_bits(seventh));
        encode(&positions)
    };
    let mut ext_positions: Vec<u32> = Vec::new();
    for &ext in extensions {
        ext_positions.extend_from_slice(extension_bits(ext));
    }
    let exts = encode(&ext_positions);
    core | exts
}

// strip_left / strip_right / semitones_apart_ascending live in helpers.rs and are
// re-exported at crate level via `pub use helpers::*` in lib.rs.
