//! Native unit tests for the pure language core (`tonalis`) — chord-grammar acceptance/rejection
//! and parser-level findings. The codec asserts (SCRUBBED involution, compile_dsl roundtrip) live
//! in the `SCRUBBED` crate's tests. Complements the data-driven conformance gate.

use tonalis::{is_valid_chord, lint, parse_dsl};
use tonalis::ast::Severity;

#[test]
fn chord_grammar_accepts_real_constructs() {
    for ok in [
        "C",
        "C-7",
        "C^7",
        "C^",
        "C^9",
        "C^11",
        "C^13",
        "Cadd9",
        "C7susadd3",
        "C69",
        "Co7",
        "Ch7",
        "C7+",
        "Co^7",
        "C7alt",
        "Calt",
        "D-/C",
        "/A",
        "C2",
        "C4",
        "C5",
        "C7",
        "N.C.",
        "n",
        "Bb*7+*",
        "C7777",
        "Csussus",
    ] {
        assert!(is_valid_chord(ok), "expected valid: {}", ok);
    }
}

#[test]
fn chord_grammar_rejects_typos() {
    for bad in [
        "Cxyzzy", "Cgarbage", "C!!!", "Cthe", "Czzzz", "Hello", "", "Cmaj7", "Cmin7", "W/A",
    ] {
        assert!(!is_valid_chord(bad), "expected invalid: {}", bad);
    }
}

#[test]
fn conflicting_header_is_an_error_finding() {
    // A conflicting header is an `error` finding (SPEC.md §0.1). The pure core surfaces it via the
    // parse + lint findings; the codec layer is what suppresses the URL.
    let r = parse_dsl("title: A\ntitle: B\nkey: C\ntime: 4/4\n[A]\n| C |\n");
    let mut findings = r.findings;
    if let Some(chart) = &r.chart {
        findings.extend(lint(chart));
    }
    assert!(findings.iter().any(|f| f.code == "conflicting-header"));
}

#[test]
fn happy_path_parses_without_error_findings() {
    let r = parse_dsl("title: T\nkey: C\ntime: 4/4\n[A]\n| C^7 | D-7 G7 Z\n");
    let chart = r.chart.expect("happy-path chart should parse");
    let mut findings = r.findings;
    findings.extend(lint(&chart));
    assert!(!findings.iter().any(|f| f.severity == Severity::Error));
}

#[test]
fn section_shaped_token_in_measure_is_bad_chord_not_a_section() {
    // CRITICAL-1 parity: a trailing `[B]`-shaped token in a measure line must NOT be read as a
    // section (the `^`-anchored SECTION_RE/TIME_RE require a whole-line match). `[B]` here fails
    // the chord grammar -> bad-chord, the chords are NOT silently dropped. This is a pure parse/
    // lint property, independent of URL emission.
    let r = parse_dsl("title: T\nkey: C\ntime: 4/4\n[A]\n| C7 | F7 | C7 | C7 [B] Z\n");
    let mut findings = r.findings;
    if let Some(chart) = &r.chart {
        findings.extend(lint(chart));
    }
    assert!(
        findings.iter().any(|f| f.code == "bad-chord"),
        "expected bad-chord for the [B] token, got {:?}",
        findings.iter().map(|f| &f.code).collect::<Vec<_>>(),
    );
}

/// Zero out the `line` source-position artifact so identity compares lead-sheet semantics. `line`
/// is a source-line index, not part of the chart's identity; the canonical printer re-flows the
/// layout (blank line before each section, one body line per section), so absolute line numbers
/// shift while every semantic field (cells/kind/barline/nav/hints) is preserved. Mirrors the
/// Python/TS refs' `_norm`/`norm`.
fn norm(mut chart: tonalis::ast::LeadSheet) -> tonalis::ast::LeadSheet {
    for s in &mut chart.sections {
        for m in &mut s.measures {
            m.line = 0;
        }
    }
    chart
}

#[test]
fn text_serializer_round_trips() {
    // IR -> text -> IR identity over crafted cases exercising @break (a hint), @fine (a nav), a
    // repeat with nth endings, and a final `||` barline. The text printer is the inverse of the
    // canonical-form parser (the `line` artifact is normalized away — it re-flows on re-print).
    use tonalis::{parse_dsl, serialize_text};
    for dsl in [
        "title: T\nkey: C\ntime: 4/4\n[A]\n| C6 | A-7 |\n",
        "title: T\nkey: C\ntime: 4/4\n[Intro]\n| D-7 |\n@break\n[A]\n| C6 |\n",
        "title: T\nkey: C\ntime: 4/4\n[A]\n@fine\n| C6 |\n",
        "title: T\nkey: C\ntime: 4/4\n[A]\n{ | C^7 |1. A-7 } |2. F6 ||\n",
    ] {
        let ir = parse_dsl(dsl).chart.unwrap();
        let text = serialize_text(&ir);
        let ir2 = parse_dsl(&text).chart.unwrap();
        assert_eq!(norm(ir2), norm(ir), "round-trip failed for: {}", dsl);
    }
}

#[test]
fn text_emits_break_hint_and_fine_nav() {
    // @break (a hint) and @fine (a nav) survive the text printer and re-parse to identical IR.
    use tonalis::{parse_dsl, serialize_text};
    let with_break =
        "title: T\nkey: C\ntime: 4/4\n[Intro]\n| D-7 | G7 |\n@break\n[A]\n| C6 | A-7 |\n";
    let ir = parse_dsl(with_break).chart.unwrap();
    let text = serialize_text(&ir);
    assert!(text.contains("@break"), "missing @break: {}", text);
    assert_eq!(norm(parse_dsl(&text).chart.unwrap()), norm(ir));

    let with_fine = "title: T\nkey: C\ntime: 4/4\n[A]\n@fine\n| C6 |\n";
    let ir = parse_dsl(with_fine).chart.unwrap();
    let text = serialize_text(&ir);
    assert!(text.contains("@fine"), "missing @fine: {}", text);
    assert_eq!(norm(parse_dsl(&text).chart.unwrap()), norm(ir));
}

#[test]
fn text_golden_simple() {
    // The printer's emitted form is canonical: a blank line precedes each section, one body line
    // per section, leading `| `.
    use tonalis::{parse_dsl, serialize_text};
    let ir = parse_dsl("title: T\nkey: C\ntime: 4/4\n[A]\n| C6 | A-7 |\n")
        .chart
        .unwrap();
    assert_eq!(
        serialize_text(&ir),
        "title: T\nkey: C\ntime: 4/4\n\n[A]\n| C6 | A-7 |\n"
    );
}

#[test]
fn json_round_trips_with_schema_version() {
    // ast_to_json carries schema_version:1; ast_from_json is its identity inverse.
    use tonalis::ast::{ast_from_json, ast_to_json};
    use tonalis::parse_dsl;
    let ir = parse_dsl("title: T\nkey: C\ntime: 4/4\n[A]\n| C6 |\n")
        .chart
        .unwrap();
    let j = ast_to_json(&ir);
    assert_eq!(j.get("schema_version").unwrap().as_u64(), Some(1));
    let ir2 = ast_from_json(&j).unwrap();
    assert_eq!(ir, ir2);
}

#[test]
fn json_from_rejects_unknown_major_version() {
    use tonalis::ast::ast_from_json;
    use serde_json::json;
    let bad = json!({"schema_version": 999, "meta": {}, "sections": []});
    assert!(ast_from_json(&bad).is_err());
}

// --- cross-impl rejection contract: the canonical JSON is a public interface, so the Py/TS/Rust
// ports must reject the SAME malformed inputs the SAME way — an unknown kind/barline is NOT coerced
// to *A / Normal, and a string/null schema_version is NOT silently accepted as v1. Returns an Err
// (clean), never a panic. Mirrors the Python `test_serialize.py` + TS `ast.test.ts` rejections. ----

#[test]
fn json_from_rejects_unknown_section_kind() {
    use tonalis::ast::ast_from_json;
    use serde_json::json;
    // `{kind:"bridge"}` must reject, NOT coerce to *A.
    let bad = json!({
        "schema_version": 1, "meta": {},
        "sections": [{"label": "X", "kind": "bridge", "measures": []}]
    });
    assert!(ast_from_json(&bad).is_err(), "unknown kind 'bridge' must be rejected, not coerced to A");
}

#[test]
fn json_from_rejects_unknown_barline() {
    use tonalis::ast::ast_from_json;
    use serde_json::json;
    // `{barline:"double"}` must reject, NOT coerce to Normal.
    let bad = json!({
        "schema_version": 1, "meta": {},
        "sections": [{
            "label": "A", "kind": "a",
            "measures": [{
                "cells": [{"chord": "C", "beats": null, "alt": null}],
                "ending": null, "bar_open": false, "barline": "double",
                "nav": [], "hints": [], "line": 0
            }]
        }]
    });
    assert!(ast_from_json(&bad).is_err(), "unknown barline 'double' must be rejected, not coerced to Normal");
}

#[test]
fn json_from_rejects_string_and_null_schema_version() {
    use tonalis::ast::ast_from_json;
    use serde_json::{json, Value};
    // A string "2" must NOT be silently accepted as v1 (the old `as_u64()`->None->unwrap_or(1) bug).
    let s = json!({"schema_version": "2", "meta": {}, "sections": []});
    assert!(ast_from_json(&s).is_err(), "string schema_version \"2\" must be rejected");
    // A string "1" is still a string, not the integer 1 -> reject.
    let s1 = json!({"schema_version": "1", "meta": {}, "sections": []});
    assert!(ast_from_json(&s1).is_err(), "string schema_version \"1\" must be rejected (not the int 1)");
    // null must reject (not accepted as v1).
    let n = json!({"schema_version": Value::Null, "meta": {}, "sections": []});
    assert!(ast_from_json(&n).is_err(), "null schema_version must be rejected");
    // MISSING schema_version defaults to 1 (accepted).
    let ok = json!({"meta": {}, "sections": []});
    assert!(ast_from_json(&ok).is_ok(), "missing schema_version must default to 1 and be accepted");
}
