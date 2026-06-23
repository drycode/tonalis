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

use music_dsl::{parse_chord, parse_numeric, numeric_from_chord};
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
    println!("  chord / numeric / numeric_from_chord breakdown:");
    for kind in &["chord", "numeric", "numeric_from_chord"] {
        let ok_k = outputs.iter().filter(|o| o["kind"] == *kind && !o.get("error").and_then(|v| v.as_bool()).unwrap_or(false)).count();
        let err_k = outputs.iter().filter(|o| o["kind"] == *kind && o.get("error").and_then(|v| v.as_bool()).unwrap_or(false)).count();
        println!("    {}: {} ok, {} error", kind, ok_k, err_k);
    }
}
