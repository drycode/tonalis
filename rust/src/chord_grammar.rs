//! The real (anchored) iReal chord-token validator (SPEC.md §5 — the regex is authoritative).
//!
//! Transcribed VERBATIM from the normative reference regexes in SPEC.md §5.1 (which match
//! `SCRUBBED/dsl/chord_grammar.py` and `ts/src/chordGrammar.ts`). Where prose and regex
//! disagree, the REGEX wins.

use regex::Regex;
use std::sync::OnceLock;

// _QUALITY    = (?:-|\^|o|h|\+|sus)?
// _EXT        = (?:[b#]?(?:5|6|9|11|13)|\^(?:7|9|11|13)?|sus|alt|add[0-9]+|o|h|\+|2|4|7)
// _CHORD      = ^[A-G][b#]? _QUALITY (?: _EXT )* (?:/[A-G][b#]?)?$
// _SLASH_BASS = ^/[A-G][b#]?$
//
// IMPORTANT: the only digit run is `add[0-9]+` — an EXPLICIT ASCII class, NOT `\d`. The Rust
// `regex` crate's `\d` is Unicode-aware (it would match `٣`/`３`), so `add\d+` would accept
// `Cadd٣`. The polyglot contract is ASCII-only digits (SPEC.md §1.1/§5.1), so we pin `[0-9]` to
// agree with the (now ASCII-pinned) Python ref and the JS port.
const CHORD_PATTERN: &str = r"^[A-G][b#]?(?:-|\^|o|h|\+|sus)?(?:(?:[b#]?(?:5|6|9|11|13)|\^(?:7|9|11|13)?|sus|alt|add[0-9]+|o|h|\+|2|4|7))*(?:/[A-G][b#]?)?$";
const SLASH_BASS_PATTERN: &str = r"^/[A-G][b#]?$";

fn chord_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(CHORD_PATTERN).expect("CHORD_PATTERN compiles"))
}

fn slash_bass_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(SLASH_BASS_PATTERN).expect("SLASH_BASS_PATTERN compiles"))
}

/// True iff the token is a well-formed iReal chord (or a no-chord / bass marker).
///
/// Mirrors `is_valid_chord`: `N.C.` and `n` are valid; empty is invalid; the layout-star
/// artifact `*` is stripped before matching.
pub fn is_valid_chord(token: &str) -> bool {
    if token == "N.C." || token == "n" {
        return true;
    }
    if token.is_empty() {
        return false;
    }
    // Tolerate the augmented layout-star artifact (e.g. "Bb*7+*").
    let t: String = token.chars().filter(|&c| c != '*').collect();
    chord_re().is_match(&t) || slash_bass_re().is_match(&t)
}
