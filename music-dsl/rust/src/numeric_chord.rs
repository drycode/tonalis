//! `numeric_chord.rs` — numeric (Roman numeral) chord parsing and key-relative conversion.
//!
//! Port of `music_dsl/domain/chords/numeric_chord.py`.
//! Build 4 scope: `parse_numeric`, `numeric_from_chord`.

use crate::chord::{extension_from_value, get_harmonic_function, parse_chord, seventh_from_value, triad_from_value};
use crate::chord_quality::{HarmonicFunction, Seventh, Triad};
use crate::helpers::semitones_apart_ascending;
use crate::scale_degree::ScaleDegree;
use crate::transactions::SCALE_DEGREES;
use regex::Regex;
use serde::Serialize;
use std::sync::OnceLock;

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

/// Error from numeric chord operations.
#[derive(Debug)]
pub enum NumericParseError {
    EmptyNumerator,
    RegexNoMatch(String),
    UnknownDegree(String),
    IncorrectHarmonicFunction(String),
    ChordParseError(String),
}

// ---------------------------------------------------------------------------
// Public models
// ---------------------------------------------------------------------------

/// Attributes for one part of a numeric chord (numerator or denominator).
#[derive(Debug, Clone, Serialize)]
pub struct NumericChordAttrs {
    pub root: String,
    pub triad: String,
    pub seventh: String,
    pub extensions: Vec<String>,
    pub harmonic_function: String,
    pub substitution: bool,
}

/// Full numeric chord model — numerator + optional denominator (slash chord).
#[derive(Debug, Clone, Serialize)]
pub struct NumericChordModel {
    pub numerator: NumericChordAttrs,
    pub denominator: Option<NumericChordAttrs>,
}

// ---------------------------------------------------------------------------
// Regex
// ---------------------------------------------------------------------------

static NUMERIC_CHORD_REGEX: OnceLock<Regex> = OnceLock::new();

fn numeric_chord_regex() -> &'static Regex {
    NUMERIC_CHORD_REGEX.get_or_init(|| {
        // Matches a Roman-numeral root ([b#]?[ivIV]{1,4}) followed by chord suffix.
        // Uses same suffix groups as the absolute chord regex.
        Regex::new(
            r"^(?P<root>[b#]?[ivIV]{1,4})(?P<sus_short>4)?(?P<triad>sus4|sus2|sus|[ho+\-])?(?P<seventh>\^7|\^|7)?(?P<aug5>\+)?(?P<alt>alt)?(?P<sus1>sus4|sus2|sus)?(?P<ext>(?:add|[b#]?[0-9]{1,2})*?)(?P<sus2>sus4|sus2|sus)?$"
        ).expect("numeric chord regex must compile")
    })
}

// ---------------------------------------------------------------------------
// Internal: parse one numeric chord part (no slash)
// ---------------------------------------------------------------------------

/// Parse one numeric chord segment (no `/`), return attrs.
/// `sub` flag propagates from the outer parse (leading 's' already stripped).
fn parse_one(segment: &str, substitution: bool) -> Result<NumericChordAttrs, NumericParseError> {
    let caps = numeric_chord_regex()
        .captures(segment)
        .ok_or_else(|| NumericParseError::RegexNoMatch(segment.to_string()))?;

    let cap = |name: &str| caps.name(name).map(|m| m.as_str()).unwrap_or("");

    let root_str   = cap("root");
    let sus_short  = cap("sus_short");
    let triad_cap  = cap("triad");
    let seventh_cap = cap("seventh");
    let aug5       = cap("aug5");
    let alt_cap    = cap("alt");
    let sus1       = cap("sus1");
    let ext_str    = cap("ext");
    let sus2_cap   = cap("sus2");

    // Verify root is a known ScaleDegree
    let root_degree = ScaleDegree::from_value(root_str)
        .ok_or_else(|| NumericParseError::UnknownDegree(root_str.to_string()))?;

    // Sus collection (same logic as chord.rs)
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

    let triad_is_sus = matches!(triad_cap, "sus" | "sus2" | "sus4");
    if !sus_effective.is_empty() && !triad_cap.is_empty() && !triad_is_sus {
        return Err(NumericParseError::RegexNoMatch(format!(
            "triad and sus coexist: {} + {}",
            triad_cap, sus_effective
        )));
    }

    let triad_value: &str = if !sus_effective.is_empty() {
        sus_effective
    } else {
        triad_cap
    };

    let seventh_norm = if seventh_cap == "^" { "^7" } else { seventh_cap };

    // Get enum values for harmonic function computation
    let triad = triad_from_value(triad_value)
        .map_err(|e| NumericParseError::ChordParseError(format!("{}", e)))?;

    let seventh = seventh_from_value(seventh_norm)
        .map_err(|e| NumericParseError::ChordParseError(format!("{}", e)))?;

    // Alt forces minor seventh
    let seventh = if !alt_cap.is_empty() { Seventh::Minor } else { seventh };

    let mut ext_vals: Vec<String> = if !alt_cap.is_empty() {
        let mut v = vec!["alt".to_string()];
        v.extend(get_ext_strings(ext_str)?);
        v
    } else {
        get_ext_strings(ext_str)?
    };
    if !aug5.is_empty() && !ext_vals.contains(&"#5".to_string()) {
        ext_vals.push("#5".to_string());
    }

    let hf = get_harmonic_function(triad, seventh);

    // m_or_M_scaledegree: mirror Python make_chord_attrs — lower the root case for minor-quality triads.
    // Major, Augmented, and Sus4 keep the major degree; everything else (Minor, Dim, HalfDim, Sus, Sus2) lowercases.
    let root_final = match triad {
        Triad::Major | Triad::Augmented | Triad::Sus4 => root_degree,
        _ => root_degree.to_minor(),
    };

    Ok(NumericChordAttrs {
        root: root_final.value().to_string(),
        triad: triad_value.to_string(),
        seventh: seventh_norm.to_string(),
        extensions: ext_vals,
        harmonic_function: hf.name().to_string(),
        substitution,
    })
}

/// Extract extension value strings from the raw extension substring.
/// Returns an error if a token is not a known extension value (mirrors Python's
/// ValueError on invalid enum members — e.g. `b9add9` → `b99` is rejected).
fn get_ext_strings(s: &str) -> Result<Vec<String>, NumericParseError> {
    if s.is_empty() {
        return Ok(Vec::new());
    }
    let s = s.replace("add", "").replace("69", "6,9");
    let mut result = Vec::new();
    let mut pos = 0;
    let bytes = s.as_bytes();
    while pos < bytes.len() {
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
        if pos > digit_start {
            let token = &s[start..pos];
            if extension_from_value(token).is_some() {
                result.push(token.to_string());
            } else {
                return Err(NumericParseError::RegexNoMatch(format!(
                    "Unknown extension token: {}",
                    token
                )));
            }
        } else {
            // Skip separator chars (commas etc.)
            pos = if pos == start { start + 1 } else { pos };
        }
    }
    Ok(result)
}

// ---------------------------------------------------------------------------
// Public: parse_numeric
// ---------------------------------------------------------------------------

/// Parse a numeric chord string like `"ii-7"`, `"V7/V"`, `"sV7"`.
///
/// Leading `'s'` marks a substitution. A `/` separates numerator from denominator.
pub fn parse_numeric(input: &str) -> Result<NumericChordModel, NumericParseError> {
    if input.is_empty() {
        return Err(NumericParseError::EmptyNumerator);
    }

    // Split on '/': first part = numerator (+ optional leading 's'), rest = denominator
    let mut parts = input.splitn(2, '/');
    let num_raw = parts.next().unwrap_or("");
    let denom_raw = parts.next(); // Option<&str>

    if num_raw.is_empty() {
        return Err(NumericParseError::EmptyNumerator);
    }

    // Detect substitution prefix 's'
    let (num_str, substitution) = if num_raw.starts_with('s') && num_raw.len() > 1 {
        // Only treat as substitution if the rest is a valid Roman numeral part
        let rest = &num_raw[1..];
        // Quick check: next char should be b, #, or a Roman numeral letter
        let first = rest.chars().next().unwrap_or('\0');
        if first == 'b' || first == '#' || "ivIV".contains(first) {
            (rest, true)
        } else {
            (num_raw, false)
        }
    } else {
        (num_raw, false)
    };

    let numerator = parse_one(num_str, substitution)?;

    let denominator = if let Some(denom_str) = denom_raw {
        if denom_str.is_empty() {
            None
        } else {
            Some(parse_one(denom_str, false)?)
        }
    } else {
        None
    };

    Ok(NumericChordModel { numerator, denominator })
}

// ---------------------------------------------------------------------------
// Public: numeric_from_chord
// ---------------------------------------------------------------------------

/// Convert an absolute chord to a numeric chord in the given key.
///
/// `substitution = true` applies substitution branch logic:
/// - Tritone sub (A=6): valid only if the chord is Subdominant; modulates +8 semitones
/// - Dominant sub (A≠6, harmonic function=Dominant): modulates +6 semitones (tritone)
/// - Min6 sub (A=8): modulates -6 semitones
pub fn numeric_from_chord(
    key_root: &str,
    chord_str: &str,
    substitution: bool,
) -> Result<NumericChordAttrs, NumericParseError> {
    let chord = parse_chord(chord_str)
        .map_err(|e| NumericParseError::ChordParseError(format!("{}", e)))?;

    let triad = triad_from_value(&chord.triad)
        .map_err(|e| NumericParseError::ChordParseError(format!("{}", e)))?;

    // Find base scale degree
    let semitones_to_chord = semitones_apart_ascending(key_root, &chord.root);
    let base_degree = SCALE_DEGREES[semitones_to_chord as usize];

    // For diminished triads on a flat degree, use sharp spelling instead.
    let base_degree = if triad == Triad::Diminished && base_degree.is_flat() {
        base_degree.to_sharp()
    } else {
        base_degree
    };

    // m_or_M_scaledegree: minor triad quality → lowercase degree
    let base_degree = if !matches!(triad, Triad::Major | Triad::Augmented | Triad::Sus4) {
        base_degree.to_minor()
    } else {
        base_degree
    };

    // Substitution branches
    let (scale_degree, effective_sub) = if substitution {
        // A = ascending semitones from chord root to key root
        let a = semitones_apart_ascending(&chord.root, key_root);

        if a == 6 {
            // Tritone sub: chord must be Subdominant
            let hf = HarmonicFunction::from_name(&chord.harmonic_function);
            if hf != Some(HarmonicFunction::Subdominant) {
                return Err(NumericParseError::IncorrectHarmonicFunction(format!(
                    "Tritone sub requires Subdominant harmonic function, got {:?}",
                    chord.harmonic_function
                )));
            }
            // modulate(6 + 2, degree) = modulate(8, degree)
            let deg_val = base_degree.value();
            let modulated = crate::transactions::modulate(8, deg_val);
            let new_deg = ScaleDegree::from_value(&modulated)
                .ok_or_else(|| NumericParseError::UnknownDegree(modulated.clone()))?;
            (new_deg, true)
        } else if chord.harmonic_function == "Dominant" {
            // Tritone (Dominant) sub: modulate(6, degree)
            let deg_val = base_degree.value();
            let modulated = crate::transactions::modulate(6, deg_val);
            let new_deg = ScaleDegree::from_value(&modulated)
                .ok_or_else(|| NumericParseError::UnknownDegree(modulated.clone()))?;
            (new_deg, true)
        } else if a == 8 {
            // Min6 sub: modulate(-6, degree)
            let deg_val = base_degree.value();
            let modulated = crate::transactions::modulate(-6, deg_val);
            let new_deg = ScaleDegree::from_value(&modulated)
                .ok_or_else(|| NumericParseError::UnknownDegree(modulated.clone()))?;
            (new_deg, true)
        } else {
            // No substitution branch fires — treat as no-sub
            (base_degree, true)
        }
    } else {
        (base_degree, false)
    };

    let seventh = seventh_from_value(&chord.seventh)
        .map_err(|e| NumericParseError::ChordParseError(format!("{}", e)))?;
    let hf = get_harmonic_function(triad, seventh);

    Ok(NumericChordAttrs {
        root: scale_degree.value().to_string(),
        triad: chord.triad.clone(),
        seventh: chord.seventh.clone(),
        extensions: chord.extensions.clone(),
        harmonic_function: hf.name().to_string(),
        substitution: effective_sub,
    })
}

// ---------------------------------------------------------------------------
// HarmonicFunction name parsing helper
// ---------------------------------------------------------------------------

impl HarmonicFunction {
    fn from_name(name: &str) -> Option<Self> {
        match name {
            "Dominant"    => Some(HarmonicFunction::Dominant),
            "Subdominant" => Some(HarmonicFunction::Subdominant),
            "Tonic"       => Some(HarmonicFunction::Tonic),
            _             => None,
        }
    }
}
