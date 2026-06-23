//! Rust leg of the 3-way Python↔TS↔Rust differential fuzzer.
//!
//! Reads:  conformance/music-dsl/fuzz/inputs.json
//! Writes: conformance/music-dsl/fuzz/rust_out.json
//!
//! Output shape matches oracle.py: each record is either
//!   { "name": ..., "kind": ..., ..., "error": true }
//! or
//!   { "name": ..., "kind": ..., ..., "result": { <model> } }
//!
//! Run from repo root:
//!   cargo run --manifest-path music-dsl/rust/Cargo.toml --bin fuzz_runner

use music_dsl::{
    parse_chord, parse_numeric, numeric_from_chord,
    note_to_midi, chord_pitches, scale_pitches, scale_degree_pitch,
    modulate, is_diatonic, chord_in_key, scale_value,
};
use serde_json::{json, Value};
use std::fs;

// Re-use the crate's serialization helpers via direct struct access.
// Since the crate doesn't export serialization helpers, we call the
// public parse functions and serialize via serde.

fn run_chord(input: &str) -> Value {
    match parse_chord(input) {
        Ok(model) => {
            let chord_val = serde_json::to_value(&model).unwrap();
            json!({"result": {"chord": chord_val}})
        }
        Err(_) => json!({"error": true}),
    }
}

fn run_numeric(input: &str) -> Value {
    match parse_numeric(input) {
        Ok(model) => {
            let numeric_val = serde_json::to_value(&model).unwrap();
            json!({"result": {"numeric": numeric_val}})
        }
        Err(_) => json!({"error": true}),
    }
}

fn run_numeric_from_chord(key_root: &str, chord: &str, substitution: bool) -> Value {
    match numeric_from_chord(key_root, chord, substitution) {
        Ok(attrs) => {
            let numeric_val = serde_json::to_value(&attrs).unwrap();
            json!({"result": {"numeric": numeric_val}})
        }
        Err(_) => json!({"error": true}),
    }
}

fn run_chord_pitches(chord_str: &str, octave: i64) -> Value {
    match chord_pitches(chord_str, octave) {
        Ok(pitches) => json!({"result": {"pitches": pitches}}),
        Err(_) => json!({"error": true}),
    }
}

fn run_scale_pitches(root: &str, scale_name: &str, octave: i64) -> Value {
    let pitches = scale_pitches(root, scale_name, octave);
    json!({"result": {"pitches": pitches}})
}

fn run_scale_degree_pitch(degree: &str, key_root: &str, octave: i64) -> Value {
    let pitch = scale_degree_pitch(degree, key_root, octave);
    json!({"result": {"pitch": pitch}})
}

fn run_note_to_midi(note: &str, octave: i64) -> Value {
    let pitch = note_to_midi(note, octave);
    json!({"result": {"pitch": pitch}})
}

fn run_modulate(semitones: i64, note: &str) -> Value {
    let result = modulate(semitones, note);
    json!({"result": {"note": result}})
}

fn run_is_diatonic(root: &str, scale_name: &str, chord_str: &str) -> Value {
    // Pre-validate chord: if it doesn't parse, emit error (matches Python oracle which
    // raises InvalidChordStringException rather than silently returning false).
    if let Err(_) = music_dsl::parse_chord(chord_str) {
        return json!({"error": true});
    }
    let sv = scale_value(scale_name);
    let result = is_diatonic(root, sv, chord_str);
    json!({"result": {"diatonic": result}})
}

fn run_chord_in_key(numeric_str: &str, key_root: &str) -> Value {
    match chord_in_key(numeric_str, key_root) {
        Ok(model) => {
            let chord_val = serde_json::to_value(&model).unwrap();
            json!({"result": {"chord": chord_val}})
        }
        Err(_) => json!({"error": true}),
    }
}

fn main() {
    // Locate inputs.json relative to CARGO_MANIFEST_DIR (set at compile time).
    // At runtime we use the manifest dir passed via env var, or fall back to cwd-relative path.
    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR")
        .unwrap_or_else(|_| ".".to_string());
    let inputs_path = format!("{}/../../conformance/music-dsl/fuzz/inputs.json", manifest_dir);
    let out_path = format!("{}/../../conformance/music-dsl/fuzz/rust_out.json", manifest_dir);

    let inputs_text = fs::read_to_string(&inputs_path)
        .unwrap_or_else(|e| panic!("Cannot read {}: {}", inputs_path, e));
    let records: Vec<Value> = serde_json::from_str(&inputs_text)
        .expect("inputs.json must be a JSON array");

    let mut outputs: Vec<Value> = Vec::new();
    let mut errors = 0usize;

    for (i, record) in records.iter().enumerate() {
        let kind = record["kind"].as_str().unwrap_or("unknown");
        let name = format!("fuzz/{}/{:04}", kind, i);

        let outcome = match kind {
            "chord" => {
                let input = record["input"].as_str().unwrap_or("");
                run_chord(input)
            }
            "numeric" => {
                let input = record["input"].as_str().unwrap_or("");
                run_numeric(input)
            }
            "numeric_from_chord" => {
                let key_root = record["key_root"].as_str().unwrap_or("");
                let chord = record["chord"].as_str().unwrap_or("");
                let sub = record["substitution"].as_bool().unwrap_or(false);
                run_numeric_from_chord(key_root, chord, sub)
            }
            "chord_pitches" => {
                let chord = record["chord"].as_str().unwrap_or("");
                let octave = record["octave"].as_i64().unwrap_or(4);
                run_chord_pitches(chord, octave)
            }
            "scale_pitches" => {
                let root = record["root"].as_str().unwrap_or("");
                let scale = record["scale"].as_str().unwrap_or("");
                let octave = record["octave"].as_i64().unwrap_or(4);
                run_scale_pitches(root, scale, octave)
            }
            "scale_degree_pitch" => {
                let degree = record["degree"].as_str().unwrap_or("");
                let key_root = record["key_root"].as_str().unwrap_or("");
                let octave = record["octave"].as_i64().unwrap_or(4);
                run_scale_degree_pitch(degree, key_root, octave)
            }
            "note_to_midi" => {
                let note = record["note"].as_str().unwrap_or("");
                let octave = record["octave"].as_i64().unwrap_or(4);
                run_note_to_midi(note, octave)
            }
            "modulate" => {
                let semitones = record["semitones"].as_i64().unwrap_or(0);
                let note = record["note"].as_str().unwrap_or("");
                run_modulate(semitones, note)
            }
            "is_diatonic" => {
                let root = record["root"].as_str().unwrap_or("");
                let scale = record["scale"].as_str().unwrap_or("");
                let chord = record["chord"].as_str().unwrap_or("");
                run_is_diatonic(root, scale, chord)
            }
            "chord_in_key" => {
                let numeric = record["numeric"].as_str().unwrap_or("");
                let key_root = record["key_root"].as_str().unwrap_or("");
                run_chord_in_key(numeric, key_root)
            }
            _ => {
                eprintln!("WARNING: unknown kind {} at index {}", kind, i);
                continue;
            }
        };

        let is_error = outcome.get("error").and_then(|v| v.as_bool()).unwrap_or(false);
        if is_error {
            errors += 1;
        }

        let mut entry = json!({ "name": name, "kind": kind });
        // Copy input keys
        match kind {
            "chord" | "numeric" => {
                entry["input"] = record["input"].clone();
            }
            "numeric_from_chord" => {
                entry["key_root"] = record["key_root"].clone();
                entry["chord"] = record["chord"].clone();
                entry["substitution"] = record["substitution"].clone();
            }
            "chord_pitches" => {
                entry["chord"] = record["chord"].clone();
                entry["octave"] = record["octave"].clone();
            }
            "scale_pitches" => {
                entry["root"] = record["root"].clone();
                entry["scale"] = record["scale"].clone();
                entry["octave"] = record["octave"].clone();
            }
            "scale_degree_pitch" => {
                entry["degree"] = record["degree"].clone();
                entry["key_root"] = record["key_root"].clone();
                entry["octave"] = record["octave"].clone();
            }
            "note_to_midi" => {
                entry["note"] = record["note"].clone();
                entry["octave"] = record["octave"].clone();
            }
            "modulate" => {
                entry["semitones"] = record["semitones"].clone();
                entry["note"] = record["note"].clone();
            }
            "is_diatonic" => {
                entry["root"] = record["root"].clone();
                entry["scale"] = record["scale"].clone();
                entry["chord"] = record["chord"].clone();
            }
            "chord_in_key" => {
                entry["numeric"] = record["numeric"].clone();
                entry["key_root"] = record["key_root"].clone();
            }
            _ => {}
        }
        if is_error {
            entry["error"] = json!(true);
        } else {
            entry["result"] = outcome["result"].clone();
        }

        outputs.push(entry);
    }

    let out_text = serde_json::to_string_pretty(&outputs).unwrap() + "\n";
    fs::write(&out_path, out_text)
        .unwrap_or_else(|e| panic!("Cannot write {}: {}", out_path, e));

    println!("Rust fuzz runner: {} outputs -> {}", outputs.len(), out_path);

    let _ok = outputs.len() - errors;
    println!("  breakdown by kind:");
    for kind in &[
        "chord", "numeric", "numeric_from_chord",
        "chord_pitches", "scale_pitches", "scale_degree_pitch", "note_to_midi",
        "modulate", "is_diatonic", "chord_in_key",
    ] {
        let ok_k = outputs.iter().filter(|o| o["kind"] == *kind && !o.get("error").and_then(|v| v.as_bool()).unwrap_or(false)).count();
        let err_k = outputs.iter().filter(|o| o["kind"] == *kind && o.get("error").and_then(|v| v.as_bool()).unwrap_or(false)).count();
        println!("    {}: {} ok, {} error", kind, ok_k, err_k);
    }
}
