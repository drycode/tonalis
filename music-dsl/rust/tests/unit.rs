use music_dsl::{intervals_equal, interval_semitones, notes_equal, note_index, scale_degrees_equal};

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
