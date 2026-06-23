//! music-dsl conformance gate. Loads conformance/music-dsl/cases/ ** /*.json, dispatches each
//! case's `op` against the crate, asserts `expect.value` (or `expect.error`), and asserts the
//! frozen case count.
//! Cases tree is read relative to CARGO_MANIFEST_DIR (music-dsl/rust/ -> ../../conformance/music-dsl/cases).
use music_dsl::{
    chord_encoding, encoding_value, interval_semitones, intervals_equal, note_index,
    notes_equal, parse_chord, scale_degrees_equal, scale_value, semitones_apart_ascending,
    strip_left, strip_right,
};
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};

const EXPECTED_CASE_COUNT: usize = 216; // keep in sync with Python/TS runners

fn cases_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("conformance")
        .join("music-dsl")
        .join("cases")
}

fn collect_json(dir: &Path, out: &mut Vec<PathBuf>) {
    for entry in fs::read_dir(dir).unwrap() {
        let path = entry.unwrap().path();
        if path.is_dir() {
            collect_json(&path, out);
        } else if path.extension().and_then(|e| e.to_str()) == Some("json") {
            out.push(path);
        }
    }
}

/// Sentinel value returned by dispatch to signal that the op errored (for `expect.error` cases).
const ERROR_SENTINEL: &str = "__ERROR__";

/// Dispatch an op. Returns:
/// - `Value::String(ERROR_SENTINEL)` when the op produces a recoverable error
///   (strip_left / strip_right out-of-range).
/// - A JSON-comparable `Value` otherwise.
fn dispatch(op: &str, args: &Value) -> Value {
    let s = |k: &str| args.get(k).and_then(|v| v.as_str()).unwrap();
    let u = |k: &str| args.get(k).and_then(|v| v.as_u64()).unwrap();

    match op {
        // Build 1 ops
        "intervals_equal" => Value::Bool(intervals_equal(s("a"), s("b"))),
        "interval_semitones" => Value::from(interval_semitones(s("x"))),
        "notes_equal" => Value::Bool(notes_equal(s("a"), s("b"))),
        "note_index" => Value::from(note_index(s("n"))),
        "scale_degrees_equal" => Value::Bool(scale_degrees_equal(s("a"), s("b"))),

        // Build 2 ops
        "scale_value" => Value::from(scale_value(s("name"))),

        "encoding_value" => {
            let triad = s("triad");
            let seventh = s("seventh");
            let exts_val = args.get("extensions").expect("missing extensions");
            let exts: Vec<&str> = exts_val
                .as_array()
                .expect("extensions must be array")
                .iter()
                .map(|v| v.as_str().expect("extension must be string"))
                .collect();
            Value::from(encoding_value(triad, seventh, &exts))
        }

        "strip_left" => {
            let bits = u("bits");
            let x = args.get("x").and_then(|v| v.as_u64()).unwrap() as u32;
            match strip_left(bits, x) {
                Ok(v) => Value::from(v),
                Err(_) => Value::String(ERROR_SENTINEL.to_string()),
            }
        }

        "strip_right" => {
            let bits = u("bits");
            let x = args.get("x").and_then(|v| v.as_u64()).unwrap() as u32;
            match strip_right(bits, x) {
                Ok(v) => Value::from(v),
                Err(_) => Value::String(ERROR_SENTINEL.to_string()),
            }
        }

        "semitones_apart_ascending" => {
            Value::from(semitones_apart_ascending(s("root"), s("note")))
        }

        // Build 3 ops
        "parse_chord" => {
            let input = s("input");
            match parse_chord(input) {
                Ok(model) => {
                    let chord_val = serde_json::to_value(&model).unwrap();
                    let mut map = serde_json::Map::new();
                    map.insert("chord".to_string(), chord_val);
                    Value::Object(map)
                }
                Err(_) => Value::String(ERROR_SENTINEL.to_string()),
            }
        }

        "encode_chord" => {
            let input = s("input");
            match chord_encoding(input) {
                Ok(v) => Value::from(v),
                Err(_) => Value::String(ERROR_SENTINEL.to_string()),
            }
        }

        other => panic!("unknown op {}", other),
    }
}

#[test]
fn conformance_all_cases() {
    let dir = cases_dir();
    let mut files = Vec::new();
    collect_json(&dir, &mut files);
    files.sort();

    let mut total = 0usize;
    let mut failures = Vec::new();

    for path in &files {
        let arr: Vec<Value> =
            serde_json::from_str(&fs::read_to_string(path).unwrap()).unwrap();
        for case in arr {
            total += 1;
            let got = dispatch(case["op"].as_str().unwrap(), &case["args"]);
            let expect = &case["expect"];

            // Determine case type: error, model (parse_chord), or value.
            let is_error_case = expect
                .get("error")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            let is_model_case = expect.get("model").is_some();

            if is_error_case {
                // Op must have returned the error sentinel.
                if got != Value::String(ERROR_SENTINEL.to_string()) {
                    failures.push(format!(
                        "{}: op={} expected error but got={}",
                        case["name"], case["op"], got
                    ));
                }
            } else if is_model_case {
                let want = &expect["model"];
                if &got != want {
                    failures.push(format!(
                        "{}: op={} got={} want={}",
                        case["name"], case["op"], got, want
                    ));
                }
            } else {
                let want = &expect["value"];
                if &got != want {
                    failures.push(format!(
                        "{}: op={} got={} want={}",
                        case["name"], case["op"], got, want
                    ));
                }
            }
        }
    }

    assert_eq!(total, EXPECTED_CASE_COUNT, "case count drifted");
    assert!(
        failures.is_empty(),
        "music-dsl conformance failures:\n{}",
        failures.join("\n")
    );
}
