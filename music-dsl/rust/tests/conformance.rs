//! music-dsl conformance gate. Loads conformance/music-dsl/cases/ ** /*.json, dispatches each
//! case's `op` against the crate, asserts `expect.value` (or `expect.error`), and asserts the
//! frozen case count.
//! Cases tree is read relative to CARGO_MANIFEST_DIR (music-dsl/rust/ -> ../../conformance/music-dsl/cases).
use music_dsl::{
    chord_encoding, chord_in_key, chord_pitches, contains, encoding_value,
    harmonic_function_in_key, interval_pitches, interval_semitones, intervals_equal, is_diatonic,
    midi_to_hz, modulate, note_index, note_to_midi, notes_equal, numeric_from_chord, parse_chord,
    parse_measure, parse_numeric, scale_degree_pitch, scale_degrees_equal, scale_descriptor,
    scale_pitches, scale_value, semitones_apart_ascending, strip_left, strip_right, TimeSignature,
};
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};

const EXPECTED_CASE_COUNT: usize = 429; // keep in sync with Python/TS runners

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

        "scale_contains" => {
            let name = s("name");
            let pitch_class = u("pitch_class") as u32;
            Value::Bool(contains(scale_descriptor(name), pitch_class))
        }

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

        // Build 4 ops
        "parse_numeric" => {
            let input = s("input");
            match parse_numeric(input) {
                Ok(model) => {
                    let numeric_val = serde_json::to_value(&model).unwrap();
                    let mut map = serde_json::Map::new();
                    map.insert("numeric".to_string(), numeric_val);
                    Value::Object(map)
                }
                Err(_) => Value::String(ERROR_SENTINEL.to_string()),
            }
        }

        "numeric_from_chord" => {
            let key_root = s("key_root");
            let chord = s("chord");
            let sub = args.get("substitution").and_then(|v| v.as_bool()).unwrap_or(false);
            match numeric_from_chord(key_root, chord, sub) {
                Ok(attrs) => {
                    let numeric_val = serde_json::to_value(&attrs).unwrap();
                    let mut map = serde_json::Map::new();
                    map.insert("numeric".to_string(), numeric_val);
                    Value::Object(map)
                }
                Err(_) => Value::String(ERROR_SENTINEL.to_string()),
            }
        }

        "modulate" => {
            let semitones = args.get("semitones").and_then(|v| v.as_i64()).unwrap();
            let note = s("note");
            match modulate(semitones, note) {
                Ok(result) => Value::String(result),
                Err(_) => Value::String(ERROR_SENTINEL.to_string()),
            }
        }

        "is_diatonic" => {
            let root = s("root");
            let scale_name = s("scale");
            let chord = s("chord");
            let scale = scale_descriptor(scale_name);
            match is_diatonic(root, scale, chord) {
                Ok(v) => Value::Bool(v),
                Err(_) => Value::String(ERROR_SENTINEL.to_string()),
            }
        }

        "harmonic_function_in_key" => {
            let key_root = s("key_root");
            let key_is_minor = args.get("key_is_minor").and_then(|v| v.as_bool()).unwrap_or(false);
            let chord = s("chord");
            match harmonic_function_in_key(key_root, key_is_minor, chord) {
                Ok(result) => Value::String(result),
                Err(_) => Value::String(ERROR_SENTINEL.to_string()),
            }
        }

        "chord_in_key" => {
            let numeric = s("numeric");
            let key_root = s("key_root");
            match chord_in_key(numeric, key_root) {
                Ok(model) => {
                    let chord_val = serde_json::to_value(&model).unwrap();
                    let mut map = serde_json::Map::new();
                    map.insert("chord".to_string(), chord_val);
                    Value::Object(map)
                }
                Err(_) => Value::String(ERROR_SENTINEL.to_string()),
            }
        }

        // Build 5 ops (realize + time)
        "note_to_midi" => {
            let note = s("note");
            let octave = args.get("octave").and_then(|v| v.as_i64()).unwrap_or(4);
            Value::from(note_to_midi(note, octave))
        }

        "midi_to_hz" => {
            let midi = args.get("midi").and_then(|v| v.as_i64()).unwrap();
            Value::from(midi_to_hz(midi))
        }

        "interval_pitches" => {
            let root = s("root");
            let interval = s("interval");
            let octave = args.get("octave").and_then(|v| v.as_i64()).unwrap_or(4);
            let pitches = interval_pitches(root, interval, octave);
            serde_json::to_value(pitches).unwrap()
        }

        "chord_pitches" => {
            let chord = s("chord");
            let octave = args.get("octave").and_then(|v| v.as_i64()).unwrap_or(4);
            match chord_pitches(chord, octave) {
                Ok(pitches) => serde_json::to_value(pitches).unwrap(),
                Err(_) => Value::String(ERROR_SENTINEL.to_string()),
            }
        }

        "scale_pitches" => {
            let key_root = s("key_root");
            let scale = s("scale");
            let octave = args.get("octave").and_then(|v| v.as_i64()).unwrap_or(4);
            let pitches = scale_pitches(key_root, scale, octave);
            serde_json::to_value(pitches).unwrap()
        }

        "scale_degree_pitch" => {
            let degree = s("degree");
            let key_root = s("key_root");
            let octave = args.get("octave").and_then(|v| v.as_i64()).unwrap_or(4);
            Value::from(scale_degree_pitch(degree, key_root, octave))
        }

        "parse_measure" => {
            let m_number = args.get("m_number").and_then(|v| v.as_i64()).unwrap();
            let numerator = args.get("numerator").and_then(|v| v.as_i64()).unwrap();
            let denominator = args.get("denominator").and_then(|v| v.as_i64()).unwrap();
            let raw_measure = s("raw_measure");
            let ts = TimeSignature { numerator, denominator };
            match parse_measure(m_number, ts, raw_measure) {
                Ok(model) => {
                    let measure_val = serde_json::to_value(&model).unwrap();
                    let mut map = serde_json::Map::new();
                    map.insert("measure".to_string(), measure_val);
                    Value::Object(map)
                }
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
