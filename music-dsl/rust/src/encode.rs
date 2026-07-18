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
// Scale catalog (36-bit masks, twelve-tone pattern × 3) + two-tier descriptors
// ---------------------------------------------------------------------------

/// Build a scale's 36-bit mask from its pitch classes (semitones above the
/// tonic, 0–11). The 12-bit pattern (MSB = tonic) is repeated ×3 so the modal
/// scan can rotate to any root without the sliding window falling off the
/// most-significant end.
///
/// # Why three copies
///
/// A scale is a 12-bit mask (MSB = root, one bit per semitone). Diatonicity and
/// pitch queries ask about a *modal window* — the same scale read starting from
/// an arbitrary degree — which means rotating the 12-bit pattern by up to 11
/// positions. Storing a single 12-bit copy would force a wrap-around (bits that
/// fall off the low end reappear at the top) that plain shifts can't express.
///
/// Concatenating the pattern three times (36 bits) turns every rotation into a
/// straight left/right shift into the middle copy: `strip_left`/`strip_right`
/// can align any window from root to the octave-plus-a-fifth without special
/// wrap-around handling. This mirrors Python's `_scale_mask` exactly, so the
/// masks are derived — never hand-written literals.
pub const fn scale_mask(pitch_classes: &[u32]) -> u64 {
    let mut pattern: u64 = 0;
    let mut i = 0;
    while i < pitch_classes.len() {
        pattern |= 1u64 << (11 - pitch_classes[i]);
        i += 1;
    }
    (pattern << 24) | (pattern << 12) | pattern
}

/// Everything the library needs to know about a scale.
///
/// `mask` is the 12-bit pitch-class set repeated ×3 (36 bits). `name` is the
/// canonical display name and `category` its family. `supports_diatonic_function`
/// drives the two-tier model: membership (`contains`) is defined for every scale,
/// but functional queries (`is_diatonic` / harmonic function) are only meaningful
/// where a tonal hierarchy exists. Symmetric/atonal scales set this `false` and
/// those queries refuse (`Err`) rather than return an authoritative-looking answer.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ScaleDescriptor {
    pub mask: u64,
    pub name: &'static str,
    pub category: &'static str,
    pub supports_diatonic_function: bool,
}

/// A functional scale (has a tonal hierarchy; diatonic queries are defined).
const fn fscale(pcs: &[u32], name: &'static str, category: &'static str) -> ScaleDescriptor {
    ScaleDescriptor { mask: scale_mask(pcs), name, category, supports_diatonic_function: true }
}

/// A symmetric/atonal scale (no tonal-function model; membership only).
const fn sscale(pcs: &[u32], name: &'static str, category: &'static str) -> ScaleDescriptor {
    ScaleDescriptor { mask: scale_mask(pcs), name, category, supports_diatonic_function: false }
}

/// The frozen scale catalog, keyed by enum-member name (the conformance lookup key).
///
/// Mirrors `music_dsl.encode.Scales` (37 scales). Masks are derived from pitch-class
/// sets via [`scale_mask`], so they equal the blessed `scale_value` numbers exactly.
pub static SCALES: &[(&str, ScaleDescriptor)] = &[
    // --- Modes of the major scale (functional) --------------------------------
    ("Major",           fscale(&[0, 2, 4, 5, 7, 9, 11], "Major (Ionian)", "major-mode")),
    ("Dorian",          fscale(&[0, 2, 3, 5, 7, 9, 10], "Dorian", "major-mode")),
    ("Phrygian",        fscale(&[0, 1, 3, 5, 7, 8, 10], "Phrygian", "major-mode")),
    ("Lydian",          fscale(&[0, 2, 4, 6, 7, 9, 11], "Lydian", "major-mode")),
    ("Mixolydian",      fscale(&[0, 2, 4, 5, 7, 9, 10], "Mixolydian", "major-mode")),
    ("Minor",           fscale(&[0, 2, 3, 5, 7, 8, 10], "Natural minor (Aeolian)", "major-mode")),
    ("Locrian",         fscale(&[0, 1, 3, 5, 6, 8, 10], "Locrian", "major-mode")),

    // --- Melodic minor and its modes (functional) -----------------------------
    ("MelodicMinor",    fscale(&[0, 2, 3, 5, 7, 9, 11], "Melodic minor", "melodic-minor")),
    ("DorianFlat2",     fscale(&[0, 1, 3, 5, 7, 9, 10], "Dorian b2", "melodic-minor")),
    ("LydianAugmented", fscale(&[0, 2, 4, 6, 8, 9, 11], "Lydian augmented", "melodic-minor")),
    ("LydianDominant",  fscale(&[0, 2, 4, 6, 7, 9, 10], "Lydian dominant", "melodic-minor")),
    ("MixolydianFlat6", fscale(&[0, 2, 4, 5, 7, 8, 10], "Mixolydian b6", "melodic-minor")),
    ("LocrianNatural2", fscale(&[0, 2, 3, 5, 6, 8, 10], "Locrian natural 2", "melodic-minor")),
    ("Altered",         fscale(&[0, 1, 3, 4, 6, 8, 10], "Altered (Super Locrian)", "melodic-minor")),

    // --- Harmonic minor and its modes (functional) ----------------------------
    ("HarmonicMinor",   fscale(&[0, 2, 3, 5, 7, 8, 11], "Harmonic minor", "harmonic-minor")),
    ("LocrianNatural6", fscale(&[0, 1, 3, 5, 6, 9, 10], "Locrian natural 6", "harmonic-minor")),
    ("IonianSharp5",    fscale(&[0, 2, 4, 5, 8, 9, 11], "Ionian #5", "harmonic-minor")),
    ("DorianSharp4",    fscale(&[0, 2, 3, 6, 7, 9, 10], "Dorian #4 (Ukrainian)", "harmonic-minor")),
    ("PhrygianDominant", fscale(&[0, 1, 4, 5, 7, 8, 10], "Phrygian dominant", "harmonic-minor")),
    ("LydianSharp2",    fscale(&[0, 3, 4, 6, 7, 9, 11], "Lydian #2", "harmonic-minor")),
    ("Ultralocrian",    fscale(&[0, 1, 3, 4, 6, 8, 9], "Ultralocrian", "harmonic-minor")),

    // --- Harmonic major and other named heptatonics (functional) --------------
    ("HarmonicMajor",   fscale(&[0, 2, 4, 5, 7, 8, 11], "Harmonic major", "harmonic-major")),
    ("DoubleHarmonic",  fscale(&[0, 1, 4, 5, 7, 8, 11], "Double harmonic (Byzantine)", "exotic")),
    ("HungarianMinor",  fscale(&[0, 2, 3, 6, 7, 8, 11], "Hungarian minor", "exotic")),
    ("HungarianMajor",  fscale(&[0, 3, 4, 6, 7, 9, 10], "Hungarian major", "exotic")),
    ("NeapolitanMajor", fscale(&[0, 1, 3, 5, 7, 9, 11], "Neapolitan major", "exotic")),
    ("NeapolitanMinor", fscale(&[0, 1, 3, 5, 7, 8, 11], "Neapolitan minor", "exotic")),

    // --- Pentatonic and blues (functional) ------------------------------------
    ("MajorPentatonic", fscale(&[0, 2, 4, 7, 9], "Major pentatonic", "pentatonic")),
    ("MinorPentatonic", fscale(&[0, 3, 5, 7, 10], "Minor pentatonic", "pentatonic")),
    ("Blues",           fscale(&[0, 3, 5, 6, 7, 10], "Blues (minor)", "blues")),

    // --- Bebop (functional, 8-note; passing tone documented in SPEC) -----------
    ("BebopDominant",   fscale(&[0, 2, 4, 5, 7, 9, 10, 11], "Bebop dominant", "bebop")),
    ("BebopMajor",      fscale(&[0, 2, 4, 5, 7, 8, 9, 11], "Bebop major", "bebop")),
    ("BebopDorian",     fscale(&[0, 2, 3, 4, 5, 7, 9, 10], "Bebop Dorian", "bebop")),
    ("BebopMinor",      fscale(&[0, 2, 3, 5, 7, 9, 10, 11], "Bebop minor", "bebop")),

    // --- Symmetric / atonal (NON-functional: membership only) -----------------
    ("WholeTone",           sscale(&[0, 2, 4, 6, 8, 10], "Whole tone", "symmetric")),
    ("DiminishedHalfWhole", sscale(&[0, 1, 3, 4, 6, 7, 9, 10], "Diminished (half-whole)", "symmetric")),
    ("DiminishedWholeHalf", sscale(&[0, 2, 3, 5, 6, 8, 9, 11], "Diminished (whole-half)", "symmetric")),
    ("Augmented",           sscale(&[0, 3, 4, 7, 8, 11], "Augmented", "symmetric")),
    ("Chromatic",           sscale(&[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], "Chromatic", "atonal")),
];

/// Look up a scale descriptor by its enum-member name (`"Major"`, `"WholeTone"`, …).
///
/// Panics on an unknown name, mirroring the Python reference's `Scales[...]` lookup.
pub fn scale_descriptor(name: &str) -> &'static ScaleDescriptor {
    SCALES
        .iter()
        .find(|(n, _)| *n == name)
        .map(|(_, d)| d)
        .unwrap_or_else(|| panic!("unknown scale name: {}", name))
}

/// Return the numeric scale value (36-bit mask) by name.
pub fn scale_value(name: &str) -> u64 {
    scale_descriptor(name).mask
}

/// Tier-1 membership: `true` if `pitch_class` (semitones above the tonic) is in
/// the scale. Defined for EVERY scale — including symmetric/atonal scales whose
/// functional queries refuse. Mirrors `music_dsl.encode.contains`.
pub fn contains(scale: &ScaleDescriptor, pitch_class: u32) -> bool {
    let mask = scale.mask;
    let size = (64 - mask.leading_zeros()) / 3; // bit_length // 3
    let pattern = mask >> (2 * size); // the leading 12-bit copy
    (pattern >> (size - 1 - (pitch_class % size))) & 1 != 0
}

// ---------------------------------------------------------------------------
// EncodingMap — enum member → semitone bit positions
// ---------------------------------------------------------------------------

/// Semitone bit positions for a Triad variant.
///
/// Single source of truth for the triad→semitone table, shared with `realize.rs`
/// (`chord_pitches`) so the two never drift.
pub(crate) fn triad_bits(t: Triad) -> &'static [u32] {
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
///
/// Shared with `realize.rs`; note `chord_pitches` overrides this for the fully
/// diminished 7th (`Diminished` + `Minor` → offset 9) before consulting it.
pub(crate) fn seventh_bits(s: Seventh) -> &'static [u32] {
    match s {
        Seventh::Minor => &[10],
        Seventh::Major => &[11],
        Seventh::None  => &[],
    }
}

/// Semitone bit positions for an Extensions variant.
///
/// Single source of truth for the extension→semitone table, shared with
/// `realize.rs` (`chord_pitches`) so the two never drift.
pub(crate) fn extension_bits(e: Extensions) -> &'static [u32] {
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
    // Resolve the member names to enums, then delegate — the integer logic lives
    // in `encoding_value_from_enums` and is not duplicated here.
    let t = triad_from_name(triad);
    let s = seventh_from_name(seventh);
    let exts: Vec<Extensions> = extensions.iter().map(|&n| extension_from_name(n)).collect();
    encoding_value_from_enums(t, s, &exts)
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
