//! Deprecated: chord validation moved to `crate::chords` (music_dsl-backed). Kept as a re-export
//! shim so any `use crate::chord_grammar::is_valid_chord` still resolves. No chord regex remains.

pub use crate::chords::is_valid_chord;
