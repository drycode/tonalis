//! DSL linter: structural + chord-grammar checks over a parsed DslChart (SPEC.md §3–§5).
//! Errors block compilation; warnings don't. Uses the music_dsl-backed chord validator (`crate::chords`).
//!
//! Faithful port of `SCRUBBED/dsl/lint.py` and `ts/src/lint.ts`.

use crate::ast::{Barline, LeadSheet, LintFinding, Measure, NavItem, Severity};
use crate::chords::is_valid_chord;
use crate::parser::MAX_CHORD_TOKEN_LEN;

/// Corpus-derived known-good uneven :N layouts (4/4); all-equal splits are always fine.
fn allowed_uneven(pattern: &[u32]) -> bool {
    matches!(
        pattern,
        [2, 1, 1] | [1, 1, 1, 1] | [1, 1, 2] | [3, 1] | [1, 3] | [2, 2]
    )
}

/// Per-cell beat counts: explicit :N consume their count; unannotated split the remainder
/// evenly. Returns (pattern, ok) where ok is false if the bar can't be filled.
fn beat_pattern(measure: &Measure, numerator: i64) -> (Vec<u32>, bool) {
    let cells = &measure.cells;
    if cells.is_empty() {
        return (Vec::new(), true);
    }
    let explicit: i64 = cells.iter().filter_map(|c| c.beats).map(|b| b as i64).sum();
    let unannotated = cells.iter().filter(|c| c.beats.is_none()).count() as i64;
    let remainder = numerator - explicit;
    if unannotated > 0 {
        if remainder <= 0 || remainder % unannotated != 0 {
            return (cells.iter().map(|c| c.beats.unwrap_or(0)).collect(), false);
        }
        let each = (remainder / unannotated) as u32;
        let pattern = cells
            .iter()
            .map(|c| c.beats.unwrap_or(each))
            .collect();
        return (pattern, true);
    }
    // all explicit
    let pattern: Vec<u32> = cells.iter().map(|c| c.beats.unwrap()).collect();
    (pattern, explicit == numerator)
}

struct Findings {
    items: Vec<LintFinding>,
}

impl Findings {
    fn err(&mut self, line: u32, code: &str, msg: &str) {
        self.items.push(LintFinding {
            severity: Severity::Error,
            line,
            code: code.to_string(),
            message: msg.to_string(),
        });
    }
    fn warn(&mut self, line: u32, code: &str, msg: &str) {
        self.items.push(LintFinding {
            severity: Severity::Warning,
            line,
            code: code.to_string(),
            message: msg.to_string(),
        });
    }
}

pub fn lint(chart: &LeadSheet) -> Vec<LintFinding> {
    let mut f = Findings { items: Vec::new() };

    // Flatten (section_index, measure_index) in order.
    let mut flat: Vec<(usize, usize)> = Vec::new();
    for (si, s) in chart.sections.iter().enumerate() {
        for mi in 0..s.measures.len() {
            flat.push((si, mi));
        }
    }

    let mut numerator: i64 = chart.meta.get_time("time").unwrap_or((4, 4)).0 as i64;

    let mut balance: i64 = 0;
    let mut n_coda = 0i64;
    let mut n_segno = 0i64;
    let last_idx = flat.len() as isize - 1;

    for (idx, &(si, mi)) in flat.iter().enumerate() {
        let m = &chart.sections[si].measures[mi];
        for nav in &m.nav {
            match nav {
                NavItem::Coda => n_coda += 1,
                NavItem::Segno => n_segno += 1,
                NavItem::Time((n, _)) => numerator = *n as i64,
                _ => {}
            }
        }
        if m.bar_open {
            balance += 1;
        }
        if m.barline == Barline::RepeatEnd {
            if balance == 0 {
                f.err(m.line, "unbalanced-repeat", "'}' with no matching '{'");
            } else {
                balance -= 1;
            }
        }
        if m.barline == Barline::Final && idx as isize != last_idx {
            f.warn(m.line, "mid-final-bar", "final barline (Z/||) is not on the last measure");
        }

        // chords
        for c in &m.cells {
            // Skip is_valid_chord for tokens already flagged token-too-long (mirrors Python lint.py:79).
            if !c.chord.is_empty() && c.chord.chars().count() <= MAX_CHORD_TOKEN_LEN && !is_valid_chord(&c.chord) {
                f.err(m.line, "bad-chord", &format!("invalid chord token: {}", c.chord));
            }
            if let Some(alt) = &c.alt {
                for tok in strip_parens(alt).split_whitespace() {
                    if !is_valid_chord(tok) {
                        f.err(m.line, "bad-chord", &format!("invalid alt chord: {}", tok));
                    }
                }
            }
        }

        // empty measure
        if m.cells.is_empty() {
            f.warn(m.line, "empty-measure", "measure has no chords (emitted as N.C.)");
            continue;
        }

        // beats. Pickup relaxation only excuses an UNDER-full first/last bar (anacrusis); an
        // OVER-full bar is always wrong, even for a pickup.
        let (pattern, ok) = beat_pattern(m, numerator);
        let total: i64 = pattern.iter().map(|&b| b as i64).sum();
        let is_pickup = idx == 0 || idx as isize == last_idx;
        if total > numerator {
            f.err(m.line, "beat-sum", &format!("beats {} overflow a {}-beat bar", fmt(&pattern), numerator));
        } else if !ok && !is_pickup {
            f.err(m.line, "beat-sum", &format!("beats {} do not fill a {}-beat bar", fmt(&pattern), numerator));
        } else if ok && distinct_count(&pattern) > 1 && !allowed_uneven(&pattern) {
            f.warn(
                m.line,
                "beat-unsupported",
                &format!("uneven beat layout {} not in the allowlist; even-split fallback", fmt(&pattern)),
            );
        }
    }

    if balance != 0 {
        f.err(0, "unbalanced-repeat", &format!("{} unclosed '{{'", balance));
    }

    // an empty section (header but no measures) silently drops in render — surface it
    for section in &chart.sections {
        if section.measures.is_empty() {
            f.warn(0, "empty-section", &format!("section [{}] has no measures (dropped)", section.label));
        }
    }

    // nth endings must belong to a repeat (a section with endings needs a bar_open)
    for section in &chart.sections {
        let has_open = section.measures.iter().any(|m| m.bar_open);
        let has_ending = section.measures.iter().any(|m| m.ending.is_some());
        if has_ending && !has_open {
            let ln = section
                .measures
                .iter()
                .find(|m| m.ending.is_some())
                .map(|m| m.line)
                .unwrap_or(0);
            f.err(ln, "ending-without-repeat", "nth ending outside a repeat block");
        }
    }

    if n_coda > 2 {
        f.err(0, "coda-count", &format!("{} coda points (max 2 — the encoder cannot flatten more)", n_coda));
    } else if n_coda == 2 && n_segno == 0 {
        f.warn(0, "coda-needs-segno", "2-coda jump without @segno (will play D.C., not D.S.)");
    }

    f.items
}

/// Python tok.strip("()").
fn strip_parens(s: &str) -> String {
    s.trim_matches(|c| c == '(' || c == ')').to_string()
}

fn distinct_count(pattern: &[u32]) -> usize {
    let mut seen: Vec<u32> = Vec::new();
    for &p in pattern {
        if !seen.contains(&p) {
            seen.push(p);
        }
    }
    seen.len()
}

/// Format a tuple-ish list for the (non-normative) message.
fn fmt(pattern: &[u32]) -> String {
    let inner: Vec<String> = pattern.iter().map(|p| p.to_string()).collect();
    format!("({})", inner.join(", "))
}
