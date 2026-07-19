//! Deterministic canonical-DSL printer: LeadSheet -> DSL text (Phase 2 §1.1). Mirrors the
//! Python/TS references (`tonalis/serialize_text.py`, `ts/src/serializeText.ts`);
//! `parse_dsl(serialize_text(ir)) == ir` is gated by the conformance suite, and this is the only
//! place IR -> text lives.

use crate::ast::{Barline, Cell, LeadSheet, Measure, MetaValue, NavItem, Section};

fn header(chart: &LeadSheet) -> String {
    let mut out: Vec<String> = Vec::new();
    for k in ["title", "composer", "style", "key", "time"] {
        match chart.meta.get(k) {
            Some(MetaValue::Time((n, d))) if k == "time" => out.push(format!("time: {}/{}", n, d)),
            Some(MetaValue::Str(s)) => out.push(format!("{}: {}", k, s)),
            _ => {}
        }
    }
    out.join("\n")
}

fn cell_str(c: &Cell) -> String {
    let mut s = c.chord.clone();
    if let Some(b) = c.beats {
        s.push_str(&format!(":{}", b));
    }
    if let Some(alt) = &c.alt {
        // A single-token alt glues inline (`G7(Db7)`, the grammar's "inline alt, no space" form),
        // but a MULTI-token alt carries an interior space (`(A-7 D7)`) and the glued form
        // `G7(A-7 D7)` re-tokenizes wrong (the cell scanner `\([^)]*\)|\S+` breaks at the space).
        // Emit the separated `chord (alt)` form so `parse(serialize(ir)) == ir` holds (SPEC §2.1).
        if alt.contains(' ') {
            s.push(' ');
        }
        s.push_str(alt);
    }
    s
}

fn nav_before(m: &Measure) -> Vec<String> {
    let mut out = Vec::new();
    for item in &m.nav {
        match item {
            NavItem::Segno => out.push("@segno".to_string()),
            NavItem::Coda => out.push("@coda".to_string()),
            NavItem::Fine => out.push("@fine".to_string()),
            NavItem::Text(t) => out.push(t.clone()),
            NavItem::Time((n, d)) => out.push(format!("[time: {}/{}]", n, d)),
            NavItem::Tocoda => {} // emitted after the measure (see nav_after)
        }
    }
    out
}

fn nav_after(m: &Measure) -> Vec<String> {
    m.nav
        .iter()
        .filter(|i| matches!(i, NavItem::Tocoda))
        .map(|_| "@tocoda".to_string())
        .collect()
}

fn barline_glyph(b: Barline) -> &'static str {
    match b {
        Barline::Normal => "|",
        Barline::RepeatEnd => "}",
        Barline::Final => "||",
    }
}

fn measure_str(m: &Measure, first_on_line: bool) -> String {
    // Canonical body line: a leading "| " opens the line, measures are space-joined, and each
    // measure ends with its barline glyph. A repeat-open prefixes "{ ".
    let prefix = if m.bar_open {
        "{ "
    } else if first_on_line {
        "| "
    } else {
        ""
    };
    let mut body = String::new();
    if let Some(e) = m.ending {
        body.push_str(&format!("{}. ", e));
    }
    let cells: Vec<String> = m.cells.iter().map(cell_str).collect();
    body.push_str(&cells.join(" "));
    format!("{}{} {}", prefix, body, barline_glyph(m.barline))
}

fn section_text(s: &Section) -> String {
    // One body line per section (parser-faithful): directives (@break/@segno/.../<text>) sit on
    // their own line and FLUSH the in-progress measure line before them; @tocoda flushes after.
    let mut lines = vec![format!("[{}]", s.label)];
    let mut run: Vec<String> = Vec::new(); // measures accumulating on the current body line

    fn flush(lines: &mut Vec<String>, run: &mut Vec<String>) {
        if !run.is_empty() {
            lines.push(run.join(" "));
            run.clear();
        }
    }

    for m in &s.measures {
        let mut before: Vec<String> = Vec::new();
        for h in &m.hints {
            if h == "break" {
                before.push("@break".to_string());
            }
        }
        before.extend(nav_before(m));
        if !before.is_empty() {
            flush(&mut lines, &mut run);
            lines.extend(before);
        }
        let first_on_line = run.is_empty();
        run.push(measure_str(m, first_on_line));
        let after = nav_after(m);
        if !after.is_empty() {
            flush(&mut lines, &mut run);
            lines.extend(after);
        }
    }
    flush(&mut lines, &mut run);
    lines.join("\n")
}

/// Canonical DSL text for a LeadSheet (trailing newline; blank line before each section).
pub fn serialize_text(chart: &LeadSheet) -> String {
    let mut parts = vec![header(chart)];
    for s in &chart.sections {
        parts.push(String::new());
        parts.push(section_text(s));
    }
    parts.join("\n") + "\n"
}
