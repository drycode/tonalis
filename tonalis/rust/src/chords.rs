//! Chord-token validation for the lead-sheet linter, standing on music_dsl.
//!
//! Replaces chord_grammar's hand-rolled regex: the "is this a real chord" decision delegates to
//! music_dsl's parse_chord (the theory library is the single source of truth). The non-chord
//! lead-sheet tokens parse_chord rejects but the linter must accept are kept: "N.C."/"n" markers,
//! a standalone slash-bass continuation ("/A"), and the augmented layout-star artifact ("Bb*7+*"),
//! stripped before validating.
//!
//! One-way dependency rule (Phase 1/3): leadsheet -> music_dsl; music_dsl never imports leadsheet.

use music_dsl::parse_chord;
use regex::Regex;
use std::sync::OnceLock;

fn slash_bass_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"^/[A-G][b#]?$").expect("SLASH_BASS_PATTERN compiles"))
}

/// True iff the token is a well-formed chord (or a no-chord / bass marker).
///
/// Mirrors the TS/Python `is_valid_chord`: `N.C.`/`n` valid; empty invalid; the layout-star `*` is
/// stripped before validating; a bare slash-bass is valid; everything else delegates to music_dsl.
pub fn is_valid_chord(token: &str) -> bool {
    if token == "N.C." || token == "n" {
        return true;
    }
    if token.is_empty() {
        return false;
    }
    // Tolerate the augmented layout-star artifact (e.g. "Bb*7+*").
    let t: String = token.chars().filter(|&c| c != '*').collect();
    if slash_bass_re().is_match(&t) {
        return true;
    }
    parse_chord(&t).is_ok()
}

#[cfg(test)]
mod tests {
    use super::is_valid_chord;

    #[test]
    fn wrapper_accepts_non_chord_markers_and_real_chords() {
        for t in ["N.C.", "n", "/A", "Bb*7+*", "C-7", "F^7", "G7b9", "C4", "C7+"] {
            assert!(is_valid_chord(t), "{t} should be valid");
        }
    }

    #[test]
    fn wrapper_rejects_empty_and_malformed() {
        for t in ["", "C7777", "H9", "xyz", "9"] {
            assert!(!is_valid_chord(t), "{t} should be invalid");
        }
    }
}
