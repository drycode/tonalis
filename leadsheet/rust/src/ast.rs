//! DSL abstract syntax — the structures produced by the parser, consumed by the linter and
//! compiler — plus the canonical JSON projection that matches the conformance `ast` shape
//! (SPEC.md §2.1). Mirrors the Python reference `tonalis/ast.py` + `tonalis/serialize.py` and the
//! TypeScript port `ts/src/ast.ts`.
//!
//! Phase 2: the IR is NEUTRAL. The root is [`LeadSheet`] (was `DslChart`); a section carries a
//! neutral [`SectionKind`] (derived by the parser from the bracket name); a measure carries a
//! [`Barline`] enum (was the raw `bar_close` glyph) plus an opaque `hints` list (where `@break`
//! lives — it has no lead-sheet semantics). No field stores a format-specific value; a downstream
//! codec maps kind/barline/hints to the target format's section/barline markers itself.

use serde_json::{json, Map, Value};

/// A meter as a (numerator, denominator) pair.
pub type Time = (u32, u32);

/// A navigation item attached to a measure (SPEC.md §2.1). Tuple-shaped, like the references.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum NavItem {
    Segno,
    Coda,
    Tocoda,
    Fine,
    Text(String),
    Time(Time),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Cell {
    pub chord: String,
    /// explicit `:N`, else None (even split of the bar)
    pub beats: Option<u32>,
    /// raw "(A-7 D7)" alt-chord text including parens, or None
    pub alt: Option<String>,
}

/// Neutral right-barline. `'|'`->Normal, `'}'`->RepeatEnd, `'Z'`/`'||'`->Final.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Barline {
    Normal,
    RepeatEnd,
    Final,
}

impl Barline {
    pub fn as_str(self) -> &'static str {
        match self {
            Barline::Normal => "normal",
            Barline::RepeatEnd => "repeat_end",
            Barline::Final => "final",
        }
    }
}

/// Neutral section role, derived by the parser from the bracket name.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SectionKind {
    A,
    B,
    C,
    D,
    Intro,
    Verse,
}

impl SectionKind {
    pub fn as_str(self) -> &'static str {
        match self {
            SectionKind::A => "a",
            SectionKind::B => "b",
            SectionKind::C => "c",
            SectionKind::D => "d",
            SectionKind::Intro => "intro",
            SectionKind::Verse => "verse",
        }
    }

    pub fn from_str(s: &str) -> Option<SectionKind> {
        Some(match s {
            "a" => SectionKind::A,
            "b" => SectionKind::B,
            "c" => SectionKind::C,
            "d" => SectionKind::D,
            "intro" => SectionKind::Intro,
            "verse" => SectionKind::Verse,
            _ => return None,
        })
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Measure {
    pub cells: Vec<Cell>,
    /// 1./2. nth-ending number, or None
    pub ending: Option<u32>,
    /// preceded by '{'
    pub bar_open: bool,
    /// neutral right-barline (was the raw `bar_close` glyph)
    pub barline: Barline,
    /// semantic navigation items, in render order
    pub nav: Vec<NavItem>,
    /// opaque render-hints, e.g. "break"; NO lead-sheet semantics
    pub hints: Vec<String>,
    /// source line for findings
    pub line: u32,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Section {
    pub label: String,
    /// neutral role (the parser derives it from the bracket name)
    pub kind: SectionKind,
    pub measures: Vec<Measure>,
}

/// A metadata value: a string for title/composer/style/key, or a meter for `time`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum MetaValue {
    Str(String),
    Time(Time),
}

/// Order-preserving metadata map, mirroring the Python dict's insertion order (the canonical
/// JSON key order is the order headers were encountered — SPEC.md §2.1 / serialize.py).
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Meta {
    entries: Vec<(String, MetaValue)>,
}

impl Meta {
    pub fn new() -> Self {
        Meta { entries: Vec::new() }
    }

    pub fn contains(&self, key: &str) -> bool {
        self.entries.iter().any(|(k, _)| k == key)
    }

    pub fn get(&self, key: &str) -> Option<&MetaValue> {
        self.entries.iter().find(|(k, _)| k == key).map(|(_, v)| v)
    }

    /// First-wins insert: only inserts if the key is not already present.
    pub fn insert(&mut self, key: &str, value: MetaValue) {
        if !self.contains(key) {
            self.entries.push((key.to_string(), value));
        }
    }

    pub fn get_str(&self, key: &str) -> Option<&str> {
        match self.get(key) {
            Some(MetaValue::Str(s)) => Some(s.as_str()),
            _ => None,
        }
    }

    pub fn get_time(&self, key: &str) -> Option<Time> {
        match self.get(key) {
            Some(MetaValue::Time(t)) => Some(*t),
            _ => None,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LeadSheet {
    pub meta: Meta,
    pub sections: Vec<Section>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Severity {
    Error,
    Warning,
}

impl Severity {
    pub fn as_str(self) -> &'static str {
        match self {
            Severity::Error => "error",
            Severity::Warning => "warning",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LintFinding {
    pub severity: Severity,
    pub line: u32,
    pub code: String,
    pub message: String,
}

#[derive(Clone, Debug)]
pub struct ParseResult {
    pub chart: Option<LeadSheet>,
    pub findings: Vec<LintFinding>,
}

// --- canonical JSON projection (SPEC.md §2.1) ---------------------------------------------

fn meta_to_json(meta: &Meta) -> Value {
    // Preserve insertion order (the order headers were encountered), matching the Python dict.
    let mut out = Map::new();
    for (k, v) in &meta.entries {
        let jv = match v {
            MetaValue::Str(s) => Value::String(s.clone()),
            MetaValue::Time((n, d)) => json!([n, d]),
        };
        out.insert(k.clone(), jv);
    }
    Value::Object(out)
}

fn nav_item_to_json(item: &NavItem) -> Value {
    match item {
        NavItem::Segno => json!(["segno"]),
        NavItem::Coda => json!(["coda"]),
        NavItem::Tocoda => json!(["tocoda"]),
        NavItem::Fine => json!(["fine"]),
        NavItem::Text(s) => json!(["text", s]),
        NavItem::Time((n, d)) => json!(["time", [n, d]]),
    }
}

fn cell_to_json(c: &Cell) -> Value {
    // Fixed key order: chord, beats, alt.
    let mut m = Map::new();
    m.insert("chord".into(), Value::String(c.chord.clone()));
    m.insert(
        "beats".into(),
        match c.beats {
            Some(b) => json!(b),
            None => Value::Null,
        },
    );
    m.insert(
        "alt".into(),
        match &c.alt {
            Some(a) => Value::String(a.clone()),
            None => Value::Null,
        },
    );
    Value::Object(m)
}

fn measure_to_json(m: &Measure) -> Value {
    // Fixed key order per §2.1: cells, ending, bar_open, barline, nav, hints, line.
    let mut out = Map::new();
    out.insert(
        "cells".into(),
        Value::Array(m.cells.iter().map(cell_to_json).collect()),
    );
    out.insert(
        "ending".into(),
        match m.ending {
            Some(e) => json!(e),
            None => Value::Null,
        },
    );
    out.insert("bar_open".into(), Value::Bool(m.bar_open));
    out.insert("barline".into(), Value::String(m.barline.as_str().into()));
    out.insert(
        "nav".into(),
        Value::Array(m.nav.iter().map(nav_item_to_json).collect()),
    );
    out.insert(
        "hints".into(),
        Value::Array(m.hints.iter().map(|h| Value::String(h.clone())).collect()),
    );
    out.insert("line".into(), json!(m.line));
    Value::Object(out)
}

fn section_to_json(s: &Section) -> Value {
    let mut out = Map::new();
    out.insert("label".into(), Value::String(s.label.clone()));
    out.insert("kind".into(), Value::String(s.kind.as_str().into()));
    out.insert(
        "measures".into(),
        Value::Array(s.measures.iter().map(measure_to_json).collect()),
    );
    Value::Object(out)
}

/// Conformance/serialization schema version (SPEC.md §1.1). Carried at the canonical-JSON root;
/// `ast_from_json` rejects an unknown major version.
pub const SCHEMA_VERSION: u32 = 1;

/// Serialize a [`LeadSheet`] to the canonical JSON value (SPEC.md §2.1).
pub fn ast_to_json(chart: &LeadSheet) -> Value {
    let mut out = Map::new();
    out.insert("schema_version".into(), json!(SCHEMA_VERSION));
    out.insert("meta".into(), meta_to_json(&chart.meta));
    out.insert(
        "sections".into(),
        Value::Array(chart.sections.iter().map(section_to_json).collect()),
    );
    Value::Object(out)
}

// --- inverse: canonical JSON -> IR (SPEC.md §2.1; round-trip oracle) ----------------------------

/// Inverse of [`ast_to_json`]. Returns `Err` on malformed canonical JSON — an unknown major
/// `schema_version`, an unknown `Section.kind`, or an unknown `Measure.barline` are all rejected
/// (NOT silently coerced to `*A` / `Normal` / v1), uniformly with the Python/TS ports. The
/// canonical JSON is a public interface, so invalid input is rejected, not absorbed.
pub fn ast_from_json(v: &Value) -> Result<LeadSheet, String> {
    // Missing schema_version -> default 1 (accept). PRESENT must be exactly the integer
    // SCHEMA_VERSION: a string ("2"), null, bool, or non-1 number all reject (do NOT let a
    // non-u64 value fall through `unwrap_or(1)` and be silently accepted as v1).
    if let Some(sv) = v.get("schema_version") {
        let ok = sv.as_u64() == Some(SCHEMA_VERSION as u64);
        if !ok {
            return Err(format!(
                "unsupported schema_version {}; this build understands {}",
                sv, SCHEMA_VERSION
            ));
        }
    }
    let mut meta = Meta::new();
    if let Some(obj) = v.get("meta").and_then(|m| m.as_object()) {
        for (k, val) in obj {
            if k == "time" {
                if let Some(arr) = val.as_array() {
                    let n = arr.first().and_then(|x| x.as_u64()).unwrap_or(0) as u32;
                    let d = arr.get(1).and_then(|x| x.as_u64()).unwrap_or(0) as u32;
                    meta.insert("time", MetaValue::Time((n, d)));
                }
            } else if let Some(s) = val.as_str() {
                meta.insert(k, MetaValue::Str(s.to_string()));
            }
        }
    }
    let mut sections = Vec::new();
    if let Some(secs) = v.get("sections").and_then(|s| s.as_array()) {
        for s in secs {
            let label = s
                .get("label")
                .and_then(|l| l.as_str())
                .unwrap_or("")
                .to_string();
            let kind_str = s.get("kind").and_then(|k| k.as_str()).unwrap_or("a");
            let kind = SectionKind::from_str(kind_str)
                .ok_or_else(|| format!("unknown Section.kind {:?}", kind_str))?;
            let mut measures = Vec::new();
            if let Some(ms) = s.get("measures").and_then(|m| m.as_array()) {
                for m in ms {
                    measures.push(measure_from_json(m)?);
                }
            }
            sections.push(Section {
                label,
                kind,
                measures,
            });
        }
    }
    Ok(LeadSheet { meta, sections })
}

fn barline_from_str(s: &str) -> Result<Barline, String> {
    Ok(match s {
        "normal" => Barline::Normal,
        "repeat_end" => Barline::RepeatEnd,
        "final" => Barline::Final,
        other => return Err(format!("unknown Measure.barline {:?}", other)),
    })
}

fn measure_from_json(m: &Value) -> Result<Measure, String> {
    let cells = m
        .get("cells")
        .and_then(|c| c.as_array())
        .map(|arr| {
            arr.iter()
                .map(|c| Cell {
                    chord: c
                        .get("chord")
                        .and_then(|x| x.as_str())
                        .unwrap_or("")
                        .to_string(),
                    beats: c.get("beats").and_then(|x| x.as_u64()).map(|n| n as u32),
                    alt: c.get("alt").and_then(|x| x.as_str()).map(|s| s.to_string()),
                })
                .collect()
        })
        .unwrap_or_default();
    let ending = m.get("ending").and_then(|e| e.as_u64()).map(|n| n as u32);
    let bar_open = m.get("bar_open").and_then(|b| b.as_bool()).unwrap_or(false);
    // barline defaults to "normal" when absent, but a PRESENT-and-unknown value is rejected
    // (NOT coerced to Normal), matching the Py/TS ports.
    let barline = barline_from_str(m.get("barline").and_then(|b| b.as_str()).unwrap_or("normal"))?;
    let nav = m
        .get("nav")
        .and_then(|n| n.as_array())
        .map(|arr| arr.iter().filter_map(nav_item_from_json).collect())
        .unwrap_or_default();
    let hints = m
        .get("hints")
        .and_then(|h| h.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|x| x.as_str().map(|s| s.to_string()))
                .collect()
        })
        .unwrap_or_default();
    let line = m.get("line").and_then(|l| l.as_u64()).unwrap_or(0) as u32;
    Ok(Measure {
        cells,
        ending,
        bar_open,
        barline,
        nav,
        hints,
        line,
    })
}

fn nav_item_from_json(item: &Value) -> Option<NavItem> {
    let arr = item.as_array()?;
    let head = arr.first()?.as_str()?;
    Some(match head {
        "segno" => NavItem::Segno,
        "coda" => NavItem::Coda,
        "tocoda" => NavItem::Tocoda,
        "fine" => NavItem::Fine,
        "text" => NavItem::Text(arr.get(1)?.as_str()?.to_string()),
        "time" => {
            let t = arr.get(1)?.as_array()?;
            let n = t.first()?.as_u64()? as u32;
            let d = t.get(1)?.as_u64()? as u32;
            NavItem::Time((n, d))
        }
        _ => return None,
    })
}
