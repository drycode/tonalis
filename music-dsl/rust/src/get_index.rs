//! `get_index` — the public `note_index` and `scale_degree_index` helpers.
//! Mirrors `music_dsl/helpers.py:48 get_index()`.

use crate::notes::Note;
use crate::scale_degree::ScaleDegree;

/// Chromatic index 0–11 of a note spelling in the TWELVE_TONES flat list.
pub fn note_chromatic_index(note: Note) -> i64 {
    note.chromatic_index()
}

/// Chromatic index 0–11 of a scale degree in the SCALE_DEGREES flat-major list.
pub fn scale_degree_index(degree: ScaleDegree) -> i64 {
    degree.scale_degree_index()
}
