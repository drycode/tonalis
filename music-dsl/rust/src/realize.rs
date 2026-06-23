//! `realize.rs` — pitch realization: MIDI, Hz, and pitch-list operations.
//!
//! Port of `music_dsl/realize.py` (Build 5).
//! All MIDI values are exact integers; Hz is rounded to 4 decimal places.
//! Reuses Build-2 `Scales`/`scale_value`, Build-3 `parse_chord`, Build-4 `modulate`/`ScaleDegree`.

use crate::chord::{parse_chord, triad_from_value, seventh_from_value, extension_from_value};
use crate::chord_quality::{Triad, Seventh};
use crate::encode::scale_value;
use crate::helpers::semitones_apart_ascending;
use crate::scale_degree::ScaleDegree;
use crate::transactions::modulate;
use crate::ChordParseError;

// ---------------------------------------------------------------------------
// note_to_midi
// ---------------------------------------------------------------------------

/// Convert a note + octave to a MIDI pitch number.
///
/// `note_to_midi(C, 4) = 60` (middle C).
/// Formula: `12 * (octave + 1) + pitch_class` where
/// `pitch_class = semitones_apart_ascending(C, note)`.
pub fn note_to_midi(note: &str, octave: i64) -> i64 {
    let pitch_class = semitones_apart_ascending("C", note);
    12 * (octave + 1) + pitch_class
}

// ---------------------------------------------------------------------------
// midi_to_hz
// ---------------------------------------------------------------------------

/// Convert a MIDI pitch number to Hz (A4 = 440 Hz).
///
/// Formula: `440.0 * 2^((midi - 69) / 12)`.
/// Result is rounded to 4 decimal places for cross-runtime determinism.
pub fn midi_to_hz(midi: i64) -> f64 {
    let hz = 440.0_f64 * 2.0_f64.powf((midi as f64 - 69.0) / 12.0);
    (hz * 1e4).round() / 1e4
}

// ---------------------------------------------------------------------------
// interval_pitches
// ---------------------------------------------------------------------------

/// Return `[base, base + semitones]` where base is `note_to_midi(root, octave)`.
///
/// Mirrors `realize.py:interval_pitches(root, interval, octave)`.
pub fn interval_pitches(root: &str, interval_name: &str, octave: i64) -> Vec<i64> {
    use crate::Interval;
    let interval = Interval::from_name(interval_name)
        .unwrap_or_else(|| panic!("unknown interval: {}", interval_name));
    let base = note_to_midi(root, octave);
    vec![base, base + interval.semitones()]
}

// ---------------------------------------------------------------------------
// chord_pitches
// ---------------------------------------------------------------------------

/// Return sorted unique MIDI pitches for a chord at the given octave.
///
/// Offsets are derived from `EncodingMap` positions for triad + seventh +
/// extensions, all shifted by `base = note_to_midi(chord_root, octave)`.
///
/// **dim7 rule:** `Triad::Diminished` + `Seventh::Minor` → seventh offset = 9
/// (fully diminished 7th, e.g. `Co7`→`[60,63,66,69]`).
/// `HalfDiminished` + `Seventh::Minor` keeps offset = 10
/// (e.g. `Ch7`→`[60,63,66,70]`).
///
/// b9 extension is encoded as offset 12 (an octave above the root in the encoding,
/// i.e. `base + 12`). All other extensions follow their encoding shift values.
pub fn chord_pitches(chord_str: &str, octave: i64) -> Result<Vec<i64>, ChordParseError> {
    let model = parse_chord(chord_str)?;
    let base = note_to_midi(&model.root, octave);

    let triad = triad_from_value(&model.triad)?;
    let seventh = seventh_from_value(&model.seventh)?;

    // Triad offsets
    let triad_offsets: Vec<i64> = match triad {
        Triad::Major          => vec![4, 7],
        Triad::Minor          => vec![3, 7],
        Triad::Diminished     => vec![3, 6],
        Triad::HalfDiminished => vec![3, 6],
        Triad::Augmented      => vec![4, 8],
        Triad::Sus2           => vec![2, 7],
        Triad::Sus | Triad::Sus4 => vec![5, 7],
    };

    // Seventh offset — dim7 rule
    let seventh_offsets: Vec<i64> = match (triad, seventh) {
        (Triad::Diminished, Seventh::Minor) => vec![9],  // fully diminished 7th
        (_, Seventh::Minor) => vec![10],
        (_, Seventh::Major) => vec![11],
        (_, Seventh::None)  => vec![],
    };

    // Extension offsets (from EncodingMap bit positions)
    let mut ext_offsets: Vec<i64> = Vec::new();
    for ext_val in &model.extensions {
        if let Some(ext) = extension_from_value(ext_val) {
            use crate::chord_quality::Extensions;
            let offsets: Vec<i64> = match ext {
                Extensions::None   => vec![],
                Extensions::Add2   => vec![2],
                Extensions::Add3   => vec![4],
                Extensions::B5     => vec![6],
                Extensions::Add5   => vec![7],
                Extensions::S5     => vec![8],
                Extensions::B6     => vec![8],
                Extensions::Add6   => vec![9],
                Extensions::B9     => vec![12],  // b9 encoded as octave offset
                Extensions::Add9   => vec![13],
                Extensions::S9     => vec![14],
                Extensions::Add11  => vec![15],
                Extensions::S11    => vec![16],
                Extensions::B13    => vec![17],
                Extensions::Add13  => vec![18],
                Extensions::Alt    => vec![12, 14, 16, 17],
            };
            ext_offsets.extend(offsets);
        }
    }

    // Build sorted unique set: [0] + triad + seventh + extensions, all + base
    let mut all_offsets: Vec<i64> = vec![0];
    all_offsets.extend(&triad_offsets);
    all_offsets.extend(&seventh_offsets);
    all_offsets.extend(&ext_offsets);

    // Deduplicate and sort
    all_offsets.sort();
    all_offsets.dedup();

    Ok(all_offsets.iter().map(|&off| base + off).collect())
}

// ---------------------------------------------------------------------------
// scale_pitches
// ---------------------------------------------------------------------------

/// Return MIDI pitches for all notes in a scale, ascending from `octave`.
///
/// Uses the 36-bit `Scales` mask (stored as `u64`). Algorithm:
/// 1. `size = bit_length(value) / 3`  (where bit_length = 64 - leading_zeros)
/// 2. `top = value >> (2 * size)`  (the top `size`-bit window)
/// 3. For each bit `i` in `0..size`: if bit `size-1-i` of `top` is set → emit `base + i`
/// 4. Append `base + size` (the octave)
///
/// This reproduces the Python `scan_scale` bit read without 32-bit truncation.
pub fn scale_pitches(key_root: &str, scale_name: &str, octave: i64) -> Vec<i64> {
    let value: u64 = scale_value(scale_name);
    let base = note_to_midi(key_root, octave);

    // bit_length / 3
    let bl = 64 - value.leading_zeros(); // bit_length
    let size = (bl / 3) as i64;

    // top = value >> (2 * size)
    let top = value >> (2 * size as u32);

    let mut pitches: Vec<i64> = Vec::new();
    for i in 0..size {
        // bit i of top (from MSB): bit position = size-1-i
        if (top >> (size - 1 - i)) & 1 == 1 {
            pitches.push(base + i);
        }
    }
    // Append octave note
    pitches.push(base + size);

    pitches
}

// ---------------------------------------------------------------------------
// scale_degree_pitch
// ---------------------------------------------------------------------------

/// Return the MIDI pitch for a scale degree in the given key at the given octave.
///
/// `scale_degree_pitch(degree, key_root, octave) = note_to_midi(modulate(get_index(degree), key_root), octave)`
pub fn scale_degree_pitch(degree: &str, key_root: &str, octave: i64) -> i64 {
    let sd = ScaleDegree::from_value(degree)
        .unwrap_or_else(|| panic!("unknown scale degree: {}", degree));
    let semitones = sd.scale_degree_index();
    let note = modulate(semitones, key_root);
    note_to_midi(&note, octave)
}
