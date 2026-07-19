//! leadsheet conformance gate (SPEC.md §0.1). Loads every
//! `conformance/tonalis/cases/**/*.json`, parses+lints each `dsl`, and asserts:
//!   - `ast`     — deep-equal to `expect.ast` when present (the canonical §2.1 JSON);
//!   - `findings`— the SET of `(code, severity, line)` tuples (messages are non-normative).
//!
//! There is NO `url` assertion here — any vendor-format URL is out of scope here; it is a downstream codec's concern. The cases tree
//! is read via a path relative to `CARGO_MANIFEST_DIR` (`tonalis/rust/` -> `../../conformance/tonalis/cases`).

use tonalis::ast::{ast_from_json, ast_to_json, LeadSheet};
use tonalis::{lint, parse_dsl, serialize_text};
use serde_json::Value;
use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};

/// Zero each measure's `line` source-position artifact for text round-trip identity. The canonical
/// printer re-flows the layout (a blank line before each section), so absolute source-line numbers
/// shift while every semantic field is preserved. `IR->text->IR` compares `line`-normalized;
/// `IR->JSON->IR` keeps `line`. Mirrors the Python/TS runners + unit.rs `norm`.
fn norm(mut chart: LeadSheet) -> LeadSheet {
    for s in &mut chart.sections {
        for m in &mut s.measures {
            m.line = 0;
        }
    }
    chart
}

fn cases_dir() -> PathBuf {
    // after the tonalis/ restructure: `tonalis/rust/` -> two `..` -> repo root -> `conformance/`.
    // Before: `rust/` and `conformance/` were siblings (one `..`).
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("conformance")
        .join("tonalis")
        .join("cases")
}

/// Recursively collect every `*.json` file under `dir`.
fn collect_json(dir: &Path, out: &mut Vec<PathBuf>) {
    let entries = fs::read_dir(dir).unwrap_or_else(|e| panic!("read_dir {:?}: {}", dir, e));
    for entry in entries {
        let entry = entry.unwrap();
        let path = entry.path();
        if path.is_dir() {
            collect_json(&path, out);
        } else if path.extension().and_then(|e| e.to_str()) == Some("json") {
            out.push(path);
        }
    }
}

/// The normative finding identity: (code, severity, line). Messages are non-normative.
type FindingKey = (String, String, i64);

fn finding_set_from_expect(expect: &Value) -> BTreeSet<FindingKey> {
    let mut set = BTreeSet::new();
    if let Some(findings) = expect.get("findings").and_then(|f| f.as_array()) {
        for f in findings {
            let code = f.get("code").and_then(|c| c.as_str()).unwrap_or("").to_string();
            let severity = f
                .get("severity")
                .and_then(|s| s.as_str())
                .unwrap_or("")
                .to_string();
            let line = f.get("line").and_then(|l| l.as_i64()).unwrap_or(0);
            set.insert((code, severity, line));
        }
    }
    set
}

#[test]
fn conformance_all_cases() {
    let dir = cases_dir();
    assert!(dir.is_dir(), "cases dir not found at {:?}", dir);

    let mut files = Vec::new();
    collect_json(&dir, &mut files);
    files.sort();
    assert!(!files.is_empty(), "no conformance cases found under {:?}", dir);

    let mut passed = 0usize;
    let mut failures: Vec<String> = Vec::new();

    for path in &files {
        let text = fs::read_to_string(path).unwrap();
        let case: Value =
            serde_json::from_str(&text).unwrap_or_else(|e| panic!("parse {:?}: {}", path, e));
        let name = case
            .get("name")
            .and_then(|n| n.as_str())
            .unwrap_or("<unnamed>")
            .to_string();
        let dsl = case.get("dsl").and_then(|d| d.as_str()).unwrap_or("");
        let expect = case.get("expect").cloned().unwrap_or(Value::Null);

        let mut case_errors: Vec<String> = Vec::new();

        let parsed = parse_dsl(dsl);

        // ast — OPTIONAL, deep-equal when present.
        if let Some(expected_ast) = expect.get("ast") {
            if !expected_ast.is_null() {
                match &parsed.chart {
                    Some(chart) => {
                        let actual_ast = ast_to_json(chart);
                        if &actual_ast != expected_ast {
                            case_errors.push(format!(
                                "ast mismatch:\n   expected: {}\n   actual:   {}",
                                expected_ast, actual_ast
                            ));
                        }
                    }
                    None => {
                        case_errors.push("ast expected but parse produced no chart".to_string());
                    }
                }
            }
        }

        // findings — set of (code, severity, line). parse findings + lint findings (mirrors bless).
        if expect.get("findings").is_some() {
            let expected_set = finding_set_from_expect(&expect);
            let mut actual_set: BTreeSet<FindingKey> = parsed
                .findings
                .iter()
                .map(|f| (f.code.clone(), f.severity.as_str().to_string(), f.line as i64))
                .collect();
            if let Some(chart) = &parsed.chart {
                for f in lint(chart) {
                    actual_set.insert((f.code, f.severity.as_str().to_string(), f.line as i64));
                }
            }
            if expected_set != actual_set {
                let missing: Vec<_> = expected_set.difference(&actual_set).collect();
                let extra: Vec<_> = actual_set.difference(&expected_set).collect();
                case_errors.push(format!(
                    "findings mismatch:\n   missing: {:?}\n   extra:   {:?}",
                    missing, extra
                ));
            }
        }

        // round-trips + canonical text golden (only meaningful when there's a parseable chart).
        if let Some(chart) = &parsed.chart {
            // IR -> JSON -> IR identity is lossless (JSON carries `line`), so it holds for ANY
            // parseable chart, including degenerate findings-only/banned inputs.
            match ast_from_json(&ast_to_json(chart)) {
                Ok(back) if &back == chart => {}
                Ok(_) => {
                    case_errors.push("IR->JSON->IR round-trip is not identity".to_string())
                }
                Err(e) => case_errors.push(format!("IR->JSON->IR failed: {}", e)),
            }
            // IR -> text -> IR identity + text golden are asserted ONLY for canonical-form cases
            // (those the bless tool gave a `text` golden); banned/degenerate inputs carry none.
            if let Some(want) = expect.get("text").and_then(|t| t.as_str()) {
                let text = serialize_text(chart);
                if text != want {
                    case_errors.push("text golden mismatch".to_string());
                }
                let ok = match parse_dsl(&text).chart {
                    Some(reparsed) => norm(reparsed) == norm(parse_dsl(dsl).chart.unwrap()),
                    None => false,
                };
                if !ok {
                    case_errors.push("IR->text->IR round-trip is not identity".to_string());
                }
            }
        }

        if case_errors.is_empty() {
            passed += 1;
        } else {
            failures.push(format!(
                "FAIL [{}] ({})\n  {}",
                name,
                path.file_name().unwrap().to_string_lossy(),
                case_errors.join("\n  ")
            ));
        }
    }

    let total = files.len();
    eprintln!("leadsheet conformance: {}/{} cases passed", passed, total);
    if !failures.is_empty() {
        panic!(
            "{} of {} leadsheet conformance cases FAILED:\n\n{}",
            failures.len(),
            total,
            failures.join("\n\n")
        );
    }
}
