//! Chord parser — port of `music_dsl/domain/chords/chord.py` (`Chord` class).
//!
//! Implements `parse_chord` (→ `ChordModel`) and `chord_encoding` (→ `u64`)
//! using the same regex + dispatch logic as the Python reference.

use crate::chord_quality::{Extensions, HarmonicFunction, Seventh, Triad};
use crate::encode::encoding_value_from_enums;
use crate::notes::Note;
use regex::Regex;
use serde::Serialize;
use std::sync::OnceLock;

// ---------------------------------------------------------------------------
// Public error type
// ---------------------------------------------------------------------------

/// Opaque parse error. The message is informational; callers should match on
/// `Err(_)` rather than the inner string.
#[derive(Debug)]
pub struct ChordParseError(pub String);

impl std::fmt::Display for ChordParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "ChordParseError: {}", self.0)
    }
}

// ---------------------------------------------------------------------------
// Public model
// ---------------------------------------------------------------------------

/// Serializable chord model (mirrors Python `ChordAttrs.to_json()`).
#[derive(Debug, Clone, Serialize)]
pub struct ChordModel {
    /// Flat-normalised root value string ("C", "Db", …).
    pub root: String,
    /// Triad value string ("", "-", "h", "o", "+", "sus", "sus2", "sus4").
    pub triad: String,
    /// Seventh value string ("^7", "7", "").
    pub seventh: String,
    /// Extension value strings in parse order.
    pub extensions: Vec<String>,
    /// Harmonic-function name ("Tonic", "Dominant", "Subdominant").
    pub harmonic_function: String,
    /// Always false — Build 4 concern.
    pub substitution: bool,
}

/// Serialisation wrapper matching the conformance `expect.model` shape:
/// `{"chord": <ChordModel>}`.
#[derive(Debug, Serialize)]
pub struct ChordModelWrapper {
    pub chord: ChordModel,
}

// ---------------------------------------------------------------------------
// Regex (compiled once)
// ---------------------------------------------------------------------------

/// Named-group regex that matches the chord suffix. `sus_short` captures a
/// bare "4" that shorthand-encodes "sus4" (e.g. "C4" == "Csus4"). `aug5`
/// captures a trailing "+" after the seventh (e.g. "C7+" → seventh=7, aug5=+).
///
/// Verified byte-identical to Python via C3 probe on all 15 sus/lazy-ext
/// ambiguity inputs.
static CHORD_REGEX: OnceLock<Regex> = OnceLock::new();

fn chord_regex() -> &'static Regex {
    CHORD_REGEX.get_or_init(|| {
        Regex::new(
            r"^(?P<root>[A-G][b#]?)(?P<sus_short>4)?(?P<triad>sus4|sus2|sus|[ho+\-])?(?P<seventh>\^7|\^|7)?(?P<aug5>\+)?(?P<alt>alt)?(?P<sus1>sus4|sus2|sus)?(?P<ext>(?:add|[b#]?[0-9]{1,2})*?)(?P<sus2>sus4|sus2|sus)?$"
        ).expect("chord regex must compile")
    })
}

// ---------------------------------------------------------------------------
// Triad / Seventh / Extensions — from_value helpers
// ---------------------------------------------------------------------------

pub(crate) fn triad_from_value(s: &str) -> Result<Triad, ChordParseError> {
    match s {
        ""     => Ok(Triad::Major),
        "-"    => Ok(Triad::Minor),
        "h"    => Ok(Triad::HalfDiminished),
        "o"    => Ok(Triad::Diminished),
        "+"    => Ok(Triad::Augmented),
        "sus"  => Ok(Triad::Sus),
        "sus2" => Ok(Triad::Sus2),
        "sus4" => Ok(Triad::Sus4),
        other  => Err(ChordParseError(format!("unknown triad value: {:?}", other))),
    }
}

pub(crate) fn seventh_from_value(s: &str) -> Result<Seventh, ChordParseError> {
    match s {
        "^7" => Ok(Seventh::Major),
        "7"  => Ok(Seventh::Minor),
        ""   => Ok(Seventh::None),
        other => Err(ChordParseError(format!("unknown seventh value: {:?}", other))),
    }
}

pub(crate) fn extension_from_value(s: &str) -> Option<Extensions> {
    match s {
        "2"   => Some(Extensions::Add2),
        "3"   => Some(Extensions::Add3),
        "b5"  => Some(Extensions::B5),
        "5"   => Some(Extensions::Add5),
        "#5"  => Some(Extensions::S5),
        "b6"  => Some(Extensions::B6),
        "6"   => Some(Extensions::Add6),
        "b9"  => Some(Extensions::B9),
        "9"   => Some(Extensions::Add9),
        "#9"  => Some(Extensions::S9),
        "11"  => Some(Extensions::Add11),
        "#11" => Some(Extensions::S11),
        "b13" => Some(Extensions::B13),
        "13"  => Some(Extensions::Add13),
        "alt" => Some(Extensions::Alt),
        _     => None,
    }
}

// ---------------------------------------------------------------------------
// Extension token extraction (mirrors Python `_get_extensions`)
// ---------------------------------------------------------------------------

fn get_extensions(s: &str) -> Result<Vec<Extensions>, ChordParseError> {
    if s.is_empty() {
        return Ok(Vec::new());
    }
    // Normalise "add" prefix and "69" compound token — matches Python exactly.
    let s = s.replace("add", "").replace("69", "6,9");

    let mut exts = Vec::new();
    let mut pos = 0;
    let bytes = s.as_bytes();
    while pos < bytes.len() {
        // Match optional [b#] then 1–2 digits.
        let start = pos;
        if pos < bytes.len() && (bytes[pos] == b'b' || bytes[pos] == b'#') {
            pos += 1;
        }
        let digit_start = pos;
        // Python regex uses [0-9]{1,2} — match at most 2 digits.
        let digit_limit = (digit_start + 2).min(bytes.len());
        while pos < digit_limit && bytes[pos].is_ascii_digit() {
            pos += 1;
        }
        let digit_end = pos;
        if digit_end > digit_start {
            // We have a candidate token — look up the extension.
            let token = &s[start..digit_end];
            match extension_from_value(token) {
                Some(ext) => exts.push(ext),
                None => {
                    // Mirror Python: ValueError on unknown extension → InvalidChordStringException.
                    return Err(ChordParseError(format!(
                        "Unknown extension token: {}",
                        token
                    )));
                }
            }
        } else {
            // No digit matched — skip this character (separator, comma, etc.).
            pos = if pos == start { start + 1 } else { pos };
        }
    }
    Ok(exts)
}

// ---------------------------------------------------------------------------
// Root parsing (mirrors Python `Chord._parse_root`)
// ---------------------------------------------------------------------------

fn parse_root(s: &str) -> Result<Note, ChordParseError> {
    // White-key enharmonic spellings (identical to Python `_ENHARMONIC_ROOTS`).
    let mapped = match s {
        "Cb" => "B",
        "Fb" => "E",
        "B#" => "C",
        "E#" => "F",
        other => other,
    };
    Note::from_value(mapped)
        .map(|n| n.to_flat())
        .ok_or_else(|| ChordParseError(format!("unknown note: {:?}", mapped)))
}

// ---------------------------------------------------------------------------
// Harmonic-function table (mirrors Python `AbstractChord._get_harmonic_function`)
// ---------------------------------------------------------------------------

pub(crate) fn get_harmonic_function(triad: Triad, seventh: Seventh) -> HarmonicFunction {
    match (triad, seventh) {
        (Triad::Minor, Seventh::Minor)         => HarmonicFunction::Subdominant,
        (Triad::HalfDiminished, Seventh::Minor) => HarmonicFunction::Subdominant,
        (Triad::Major, Seventh::Minor)          => HarmonicFunction::Dominant,
        (Triad::Major, Seventh::Major)          => HarmonicFunction::Tonic,
        (Triad::Minor, Seventh::Major)          => HarmonicFunction::Tonic,
        _                                       => HarmonicFunction::Tonic,
    }
}

// ---------------------------------------------------------------------------
// Core parse implementation
// ---------------------------------------------------------------------------

/// Parse a chord string into a `ChordModel`.
///
/// Replicates Python `Chord._parse_chord_string` + `make_chord_attrs`.
pub fn parse_chord(input: &str) -> Result<ChordModel, ChordParseError> {
    // 1. Bass split — discard everything after '/'.
    let chord_part = input.split('/').next().unwrap_or(input);

    // 2. Pipe check.
    if chord_part.contains('|') {
        return Err(ChordParseError(
            "There's more than one chord in this attempt to parse".to_string(),
        ));
    }

    // 3. Regex match.
    let caps = chord_regex()
        .captures(chord_part)
        .ok_or_else(|| ChordParseError(format!("no regex match for {:?}", chord_part)))?;

    let cap = |name: &str| caps.name(name).map(|m| m.as_str()).unwrap_or("");

    // 4. Extract named groups.
    let root_str   = cap("root");
    let sus_short  = cap("sus_short");    // "4" or ""
    let triad_cap  = cap("triad");        // "sus4"/"sus2"/"sus"/"-"/"h"/"o"/"+" or ""
    let seventh_cap = cap("seventh");     // "^7"/"^"/"7" or ""
    let aug5       = cap("aug5");         // "+" or ""
    let alt_cap    = cap("alt");          // "alt" or ""
    let sus1       = cap("sus1");         // "sus4"/"sus2"/"sus" or ""
    let ext_str    = cap("ext");          // lazy extension substring
    let sus2_cap   = cap("sus2");         // "sus4"/"sus2"/"sus" or ""

    // 5. Sus collection (Python: `_sus = sus1 or sus2; if sus_short: _sus = _sus or "sus4"`).
    let _sus: &str = if !sus1.is_empty() {
        sus1
    } else if !sus2_cap.is_empty() {
        sus2_cap
    } else {
        ""
    };
    let sus_effective: &str = if sus_short == "4" && _sus.is_empty() {
        "sus4"
    } else {
        _sus
    };

    // 6. Triad+sus coexistence check.
    let triad_is_sus = matches!(triad_cap, "sus" | "sus2" | "sus4");
    if !sus_effective.is_empty() && !triad_cap.is_empty() && !triad_is_sus {
        return Err(ChordParseError(format!(
            "a triad and a sus cannot coexist ({:?} + {:?})",
            triad_cap, sus_effective
        )));
    }

    // 7. Triad resolution: prefer sus, then triad_cap, then "".
    let triad_value: &str = if !sus_effective.is_empty() {
        sus_effective
    } else {
        triad_cap
    };
    let triad = triad_from_value(triad_value)?;

    // 8. Seventh normalisation ("^" → "^7").
    let seventh_norm = if seventh_cap == "^" { "^7" } else { seventh_cap };
    let seventh = seventh_from_value(seventh_norm)?;

    // 9. Alt handling + extensions.
    let mut extensions: Vec<Extensions> = if !alt_cap.is_empty() {
        // Alt on sus is rejected.
        if matches!(triad, Triad::Sus | Triad::Sus2 | Triad::Sus4) {
            return Err(ChordParseError(
                "\"alt\" cannot modify a sus chord".to_string(),
            ));
        }
        // Alt forces minor seventh; prepends Extensions::Alt.
        let mut exts = vec![Extensions::Alt];
        exts.extend(get_extensions(ext_str)?);
        exts
    } else {
        get_extensions(ext_str)?
    };
    // aug5 (+): append S5 if not already present.
    // Runs for BOTH the alt and non-alt paths (mirrors Python reference behaviour).
    if !aug5.is_empty() && !extensions.contains(&Extensions::S5) {
        extensions.push(Extensions::S5);
    }

    // Alt forces minor seventh regardless of what the regex captured.
    let seventh = if !alt_cap.is_empty() { Seventh::Minor } else { seventh };

    // 10. Parse root.
    let note = parse_root(root_str)?;
    let root_value = note.value().to_string();

    // 11. make_chord_attrs rejection check.
    //
    // Rejects "natural root + leading b/# tension + no seventh + bare major triad"
    // (e.g. B# → C + b9 with no 7th — has no spellable canonical form).
    if triad == Triad::Major
        && seventh == Seventh::None
        && root_value.len() == 1
        && !extensions.is_empty()
        && {
            let first_val = extensions[0].value();
            first_val.starts_with('b') || first_val.starts_with('#')
        }
    {
        return Err(ChordParseError(format!(
            "{}{}: an altered tension with no seventh binds its accidental \
             to the root and has no spellable canonical form",
            root_value,
            extensions[0].value()
        )));
    }

    // 12. Harmonic function.
    let hf = get_harmonic_function(triad, seventh);

    Ok(ChordModel {
        root: root_value,
        triad: triad.value().to_string(),
        seventh: seventh.value().to_string(),
        extensions: extensions.iter().map(|e| e.value().to_string()).collect(),
        harmonic_function: hf.name().to_string(),
        substitution: false,
    })
}

// ---------------------------------------------------------------------------
// Encoding
// ---------------------------------------------------------------------------

/// Compute the 19-bit chord encoding for a chord string.
///
/// Parses the chord, re-derives the enum values (triad, seventh, extensions),
/// then calls `encoding_value_from_enums` directly — no value→name round-trip.
pub fn chord_encoding(input: &str) -> Result<u64, ChordParseError> {
    let model = parse_chord(input)?;
    let triad = triad_from_value(&model.triad)?;
    let seventh = seventh_from_value(&model.seventh)?;
    let exts: Vec<Extensions> = model
        .extensions
        .iter()
        .filter_map(|v| extension_from_value(v))
        .collect();
    Ok(encoding_value_from_enums(triad, seventh, &exts))
}
