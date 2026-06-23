use music_dsl::{
    intervals_equal, interval_semitones, notes_equal, note_index, scale_degrees_equal,
    encoding_value, scale_value, semitones_apart_ascending, strip_left, strip_right,
};

#[test]
fn notes_enharmonic_equality() {
    assert!(notes_equal("C#", "Db"));
    assert!(notes_equal("A#", "Bb"));
    assert!(!notes_equal("C", "D"));
}

#[test]
fn note_chromatic_index() {
    assert_eq!(note_index("C"), 0);
    assert_eq!(note_index("C#"), 1);
    assert_eq!(note_index("Db"), 1);
    assert_eq!(note_index("B"), 11);
}

#[test]
fn intervals_structural_and_semitones() {
    assert!(intervals_equal("m6", "m6"));
    assert!(!intervals_equal("m6", "M3")); // structural after Stage 0
    assert_eq!(interval_semitones("m6"), 8);
    assert_eq!(interval_semitones("Octave"), 12);
}

#[test]
fn scale_degree_enharmonic_equality() {
    assert!(scale_degrees_equal("#iv", "bv"));
    assert!(!scale_degrees_equal("II", "ii")); // major/minor distinct
}

// ---------------------------------------------------------------------------
// Encode layer tests (Build 2, Task 3)
// ---------------------------------------------------------------------------

#[test]
fn scales_are_reference_integers() {
    assert_eq!(scale_value("Major"), 46534580949u64);
    assert_eq!(scale_value("Minor"), 48766495578u64);
    assert_eq!(scale_value("HarmonicMinor"), 48749714265u64);
}

#[test]
fn encoding_dominant_seventh() {
    // Major triad (shifts 4,7) + Minor seventh (shift 10) + sentinel bit 18
    // bits: 18 | (18-4)=14 | (18-7)=11 | (18-10)=8
    let expected: u64 = (1 << 18) | (1 << 14) | (1 << 11) | (1 << 8);
    assert_eq!(encoding_value("Major", "Minor", &[]), expected);
}

#[test]
fn encoding_diminished_always_fixed() {
    // Diminished triad always returns DIMINISHED_ENCODING regardless of seventh
    let dim_enc = 0b1001001001000000000u64; // 299520
    assert_eq!(encoding_value("Diminished", "_None", &[]), dim_enc);
    assert_eq!(encoding_value("Diminished", "Minor", &[]), dim_enc);
    assert_eq!(encoding_value("Diminished", "Major", &[]), dim_enc);
}

#[test]
fn encoding_with_extensions() {
    // Major7 (triad[4,7] + 7th[11]) with b9 extension (shift 12)
    // sentinel 18 + bits 14,11,7,6
    let base = encoding_value("Major", "Major", &[]);
    let with_b9 = encoding_value("Major", "Major", &["b9"]);
    // b9 is shift 12 -> bit 18-13 = bit 5
    // but wait: 18 - (shift+1) = 18-13=5; bit 5 set on top of base
    assert!(with_b9 > base); // extensions add bits
    assert_eq!(with_b9 & base, base); // base bits still set
}

#[test]
fn semitones_apart_ascending_matches_reference() {
    assert_eq!(semitones_apart_ascending("C", "G"), 7);
    assert_eq!(semitones_apart_ascending("G", "C"), 5);
    assert_eq!(semitones_apart_ascending("E", "C"), 8);
    assert_eq!(semitones_apart_ascending("C", "C"), 0);
    assert_eq!(semitones_apart_ascending("Bb", "D"), 4);
}

#[test]
fn strip_right_basic() {
    // Major scale (36-bit), shift right 0 -> unchanged
    let major = scale_value("Major");
    assert_eq!(strip_right(major, 0).unwrap(), major);
    // shift right 12 -> drops low 12 bits
    let result = strip_right(major, 12).unwrap();
    assert_eq!(result, major >> 12);
}

#[test]
fn strip_right_over_length_errors() {
    // shifting more bits than bit_length should error
    let val: u64 = 0b1010u64; // bit_length = 4
    assert!(strip_right(val, 5).is_err());
}

#[test]
fn strip_left_zero_is_identity() {
    let major = scale_value("Major");
    assert_eq!(strip_left(major, 0).unwrap(), major);
}

#[test]
fn strip_left_out_of_range_errors() {
    // EMPTY_CHORD_ENCODING = 262144 < MIN_SUPPORTED? No, 262144 < 4096 is false.
    // Actually 262144 = 2^18 > MIN_SUPPORTED=4096, but strip_left raises because
    // of fidelity loss (the leading-zero check after stripping).
    // The conformance cases confirm 262144 with x=7 errors.
    assert!(strip_left(262144u64, 7).is_err());
    assert!(strip_left(299520u64, 7).is_err());
}
