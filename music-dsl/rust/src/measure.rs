//! `measure.rs` — TimeSignature + Measure (beat layout).
//!
//! Port of `music_dsl/domain/time/measure.py` + `__init__.py` (Build 5).
//! `Measure::parse` returns `Err` when a literal `%` produces an empty chord token.
//! Reuses Build-3 `parse_chord` / `ChordModel`.

use crate::chord::{parse_chord, ChordModel, ChordParseError};
use serde::Serialize;

// ---------------------------------------------------------------------------
// TimeSignature
// ---------------------------------------------------------------------------

/// Minimal time signature (numerator + denominator).
/// Only `denominator` is used in `_setup_beats`; `numerator` is stored + serialized.
#[derive(Debug, Clone, Copy, Serialize)]
pub struct TimeSignature {
    pub numerator: i64,
    pub denominator: i64,
}

// ---------------------------------------------------------------------------
// Serialisation models
// ---------------------------------------------------------------------------

/// Beat location: which measure + which beat slot (0-indexed).
#[derive(Debug, Clone, Serialize)]
pub struct BeatLocation {
    pub measure_number: i64,
    pub beat_number: i64,
}

/// One beat container: a location + optional chord (None = empty beat).
#[derive(Debug, Clone, Serialize)]
pub struct BeatContainer {
    pub beat_location: BeatLocation,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub chord: Option<ChordModel>,
}

/// Full measure model used for conformance serialisation.
#[derive(Debug, Clone, Serialize)]
pub struct MeasureModel {
    pub m_number: i64,
    pub time_signature: TimeSignature,
    pub beat_containers: Vec<Option<BeatContainerFull>>,
}

/// Serialisable beat container (for the conformance JSON model).
/// Serialises `chord` as `null` (via Option) for empty beats.
#[derive(Debug, Clone, Serialize)]
pub struct BeatContainerFull {
    pub beat_location: BeatLocation,
    pub chord: ChordModel,
}

// ---------------------------------------------------------------------------
// Wrapper for conformance output
// ---------------------------------------------------------------------------

/// Top-level conformance model: `{"measure": <MeasureModel>}`.
#[derive(Debug, Serialize)]
pub struct MeasureModelWrapper {
    pub measure: MeasureModel,
}

// ---------------------------------------------------------------------------
// parse_measure
// ---------------------------------------------------------------------------

/// Parse a raw measure string into a `MeasureModel`, or return `Err` if a
/// literal `%` produces an empty chord token.
///
/// Reproduces `Measure._setup_beats` exactly:
/// 1. `raw.replace(" ", "% ").split(" ")` — doubles every interior token.
/// 2. Pop trailing empty strings.
/// 3. `total = sum(1 + tok.count('%'))`.
/// 4. `size = max(denominator, total)`.
/// 5. Write each token across `1 + count('%')` slots; pad remaining with last chord.
/// 6. A token that strips to `""` (literal `%`) → returns `Err`.
pub fn parse_measure(
    m_number: i64,
    time_sig: TimeSignature,
    raw_measure: &str,
) -> Result<MeasureModel, ChordParseError> {
    let delimiter = " ";

    // Step 1: replace each space with "% " then split on space
    let replaced = raw_measure.replace(delimiter, "% ");
    let mut chords_list: Vec<String> = replaced
        .split(delimiter)
        .map(|s| s.to_string())
        .collect();

    // Step 2: pop trailing empty strings
    while chords_list.last().map(|s| s.is_empty()).unwrap_or(false) {
        chords_list.pop();
    }

    // Step 3: total beats = sum(1 + count('%') for each token)
    let total_beats: i64 = chords_list
        .iter()
        .map(|tok| 1 + tok.chars().filter(|&c| c == '%').count() as i64)
        .sum();

    // Step 4: size = max(denominator, total_beats)
    let size = std::cmp::max(time_sig.denominator, total_beats);

    // Build the beat containers
    let mut beat_containers: Vec<Option<BeatContainerFull>> = Vec::with_capacity(size as usize);
    let mut slot_idx: i64 = 0;
    let mut last_chord: Option<ChordModel> = None;

    // Step 5: for each token, write it across (1 + count('%')) slots
    for tok in &chords_list {
        let chord_str = tok.trim_matches('%');
        let n_slots = 1 + tok.chars().filter(|&c| c == '%').count() as i64;

        // A token that strips to "" (literal %) → error
        if chord_str.is_empty() {
            return Err(ChordParseError(
                "empty chord token (literal '%' in measure)".to_string(),
            ));
        }

        let chord = parse_chord(chord_str)?;
        last_chord = Some(chord.clone());

        for _ in 0..n_slots {
            beat_containers.push(Some(BeatContainerFull {
                beat_location: BeatLocation {
                    measure_number: m_number,
                    beat_number: slot_idx,
                },
                chord: chord.clone(),
            }));
            slot_idx += 1;
        }
    }

    // Step 5 (pad): fill remaining slots with last chord, or None if no chords
    while slot_idx < size {
        let container = last_chord.as_ref().map(|chord| BeatContainerFull {
            beat_location: BeatLocation {
                measure_number: m_number,
                beat_number: slot_idx,
            },
            chord: chord.clone(),
        });
        beat_containers.push(container);
        slot_idx += 1;
    }

    Ok(MeasureModel {
        m_number,
        time_signature: time_sig,
        beat_containers,
    })
}
