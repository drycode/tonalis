use music_dsl::{
    chord_encoding, intervals_equal, interval_semitones, notes_equal, note_index,
    parse_chord, scale_degrees_equal, encoding_value, scale_value,
    semitones_apart_ascending, strip_left, strip_right,
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

// ---------------------------------------------------------------------------
// Chord parser tests (Build 3, Task 3)
// ---------------------------------------------------------------------------

#[test]
fn chord_major7_sharp11() {
    let m = parse_chord("C^7#11").expect("C^7#11 should parse");
    assert_eq!(m.root, "C");
    assert_eq!(m.triad, "");
    assert_eq!(m.seventh, "^7");
    assert_eq!(m.extensions, vec!["#11"]);
    assert_eq!(m.harmonic_function, "Tonic");
}

#[test]
fn chord_sharp_minor7_flat_normalised() {
    // C#-7 → root normalised to Db
    let m = parse_chord("C#-7").expect("C#-7 should parse");
    assert_eq!(m.root, "Db");
    assert_eq!(m.triad, "-");
    assert_eq!(m.seventh, "7");
    assert_eq!(m.harmonic_function, "Subdominant");
}

#[test]
fn chord_sus_triad() {
    let m = parse_chord("Csus").expect("Csus should parse");
    assert_eq!(m.triad, "sus");
    assert!(m.extensions.is_empty());
}

#[test]
fn chord_c4_shorthand_sus4() {
    // "C4" is shorthand for "Csus4"
    let m = parse_chord("C4").expect("C4 should parse");
    assert_eq!(m.triad, "sus4");
    assert!(m.extensions.is_empty());
}

#[test]
fn chord_c7_plus_aug5() {
    // "C7+" → seventh=7, extensions=["#5"]
    let m = parse_chord("C7+").expect("C7+ should parse");
    assert_eq!(m.seventh, "7");
    assert_eq!(m.extensions, vec!["#5"]);
    assert_eq!(m.harmonic_function, "Dominant");
}

#[test]
fn chord_slash_bass_discarded() {
    // C^7/E should parse the same as C^7
    let m_slash = parse_chord("C^7/E").expect("C^7/E should parse");
    let m_plain = parse_chord("C^7").expect("C^7 should parse");
    assert_eq!(m_slash.root, m_plain.root);
    assert_eq!(m_slash.triad, m_plain.triad);
    assert_eq!(m_slash.seventh, m_plain.seventh);
    assert_eq!(m_slash.extensions, m_plain.extensions);
}

#[test]
fn chord_b_sharp_maps_to_c() {
    let m = parse_chord("B#").expect("B# should parse");
    assert_eq!(m.root, "C");
}

#[test]
fn chord_b_sharp_b9_rejected() {
    // B# → C (1-char root), major triad, no seventh, b9 extension → error
    assert!(parse_chord("B#b9").is_err(), "B#b9 should be rejected");
}

// ---------------------------------------------------------------------------
// Sus ambiguity regression suite (15 inputs from C3 probe)
// ---------------------------------------------------------------------------

#[test]
fn sus_ambiguity_regression() {
    struct Case { input: &'static str, triad: &'static str, seventh: &'static str, exts: Vec<&'static str> }
    let cases = [
        Case { input: "Csus",     triad: "sus",  seventh: "",    exts: vec![] },
        Case { input: "Csus4",    triad: "sus4", seventh: "",    exts: vec![] },
        Case { input: "Csus2",    triad: "sus2", seventh: "",    exts: vec![] },
        Case { input: "C4",       triad: "sus4", seventh: "",    exts: vec![] },
        Case { input: "C9sus",    triad: "sus",  seventh: "",    exts: vec!["9"] },
        Case { input: "C9sus4",   triad: "sus4", seventh: "",    exts: vec!["9"] },
        Case { input: "C7susb9",  triad: "sus",  seventh: "7",   exts: vec!["b9"] },
        Case { input: "C7b9sus",  triad: "sus",  seventh: "7",   exts: vec!["b9"] },
        Case { input: "Csus7b9",  triad: "sus",  seventh: "7",   exts: vec!["b9"] },
        Case { input: "Csus9",    triad: "sus",  seventh: "",    exts: vec!["9"] },
        Case { input: "C^",       triad: "",     seventh: "^7",  exts: vec![] },
        Case { input: "C7+",      triad: "",     seventh: "7",   exts: vec!["#5"] },
        Case { input: "Cadd9",    triad: "",     seventh: "",    exts: vec!["9"] },
        Case { input: "C69",      triad: "",     seventh: "",    exts: vec!["6","9"] },
        Case { input: "C7alt",    triad: "",     seventh: "7",   exts: vec!["alt"] },
        Case { input: "C7+alt",   triad: "",     seventh: "7",   exts: vec!["alt", "#5"] },
        Case { input: "C^7+alt",  triad: "",     seventh: "7",   exts: vec!["alt", "#5"] },
    ];
    for c in &cases {
        let m = parse_chord(c.input).unwrap_or_else(|e| panic!("{}: {}", c.input, e));
        assert_eq!(m.triad, c.triad, "{}: triad", c.input);
        assert_eq!(m.seventh, c.seventh, "{}: seventh", c.input);
        let got_exts: Vec<&str> = m.extensions.iter().map(|s| s.as_str()).collect();
        assert_eq!(got_exts, c.exts, "{}: extensions", c.input);
    }
}

#[test]
fn chord_encoding_major_triad() {
    // Major triad = sentinel(18) | triad(4,7) → 262144 | 16384 | 2048 = 280576
    assert_eq!(chord_encoding("C").unwrap(), 280576);
}

#[test]
fn chord_encoding_minor7() {
    // Minor triad + minor seventh: should not be 280576
    let enc = chord_encoding("C-7").unwrap();
    assert!(enc != 280576);
}
