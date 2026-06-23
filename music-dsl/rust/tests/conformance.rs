//! music-dsl conformance gate. Loads conformance/music-dsl/cases/ ** /*.json, dispatches each
//! case's `op` against the crate, asserts `expect.value`, and asserts the frozen case count.
//! Cases tree is read relative to CARGO_MANIFEST_DIR (music-dsl/rust/ -> ../../conformance/music-dsl/cases).
use music_dsl::{intervals_equal, interval_semitones, notes_equal, note_index, scale_degrees_equal};
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};

const EXPECTED_CASE_COUNT: usize = 51; // keep in sync with Python/TS runners

fn cases_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
        .join("conformance").join("music-dsl").join("cases")
}

fn collect_json(dir: &Path, out: &mut Vec<PathBuf>) {
    for entry in fs::read_dir(dir).unwrap() {
        let path = entry.unwrap().path();
        if path.is_dir() { collect_json(&path, out); }
        else if path.extension().and_then(|e| e.to_str()) == Some("json") { out.push(path); }
    }
}

/// Dispatch an op to a JSON value (bool ops -> Value::Bool, int ops -> Value::Number).
fn dispatch(op: &str, args: &Value) -> Value {
    let s = |k: &str| args.get(k).and_then(|v| v.as_str()).unwrap();
    match op {
        "intervals_equal"     => Value::Bool(intervals_equal(s("a"), s("b"))),
        "interval_semitones"  => Value::from(interval_semitones(s("x"))),
        "notes_equal"         => Value::Bool(notes_equal(s("a"), s("b"))),
        "note_index"          => Value::from(note_index(s("n"))),
        "scale_degrees_equal" => Value::Bool(scale_degrees_equal(s("a"), s("b"))),
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
        let arr: Vec<Value> = serde_json::from_str(&fs::read_to_string(path).unwrap()).unwrap();
        for case in arr {
            total += 1;
            let got = dispatch(case["op"].as_str().unwrap(), &case["args"]);
            let want = &case["expect"]["value"];
            if &got != want {
                failures.push(format!("{}: op={} got={} want={}",
                    case["name"], case["op"], got, want));
            }
        }
    }
    assert_eq!(total, EXPECTED_CASE_COUNT, "case count drifted");
    assert!(failures.is_empty(), "music-dsl conformance failures:\n{}", failures.join("\n"));
}
