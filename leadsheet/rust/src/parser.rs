//! Bounded, single-pass DSL parser (SPEC.md §1–§4). Never throws on arbitrary input; limit
//! violations and structural problems become findings. The parser records structure; the linter
//! (`lint.rs`) judges chord validity, beat sums, etc. Header values are read literally to EOL.
//!
//! Faithful port of `SCRUBBED/dsl/parser.py` and `ts/src/parser.ts`.

use crate::ast::{
    Barline, Cell, LeadSheet, LintFinding, Measure, Meta, MetaValue, NavItem, ParseResult, Section,
    SectionKind, Severity, Time,
};
use regex::Regex;
use std::sync::OnceLock;

pub const MAX_BYTES: usize = 256 * 1024;
pub const MAX_LINES: usize = 5000;
pub const MAX_LINE_LEN: usize = 1000;
pub const MAX_MEASURES: usize = 2000;
pub const MAX_CELLS_PER_MEASURE: usize = 16;
pub const MAX_CHORD_TOKEN_LEN: usize = 50;
pub const MAX_ALT_CHORD_TOKENS: usize = 8;
/// Numeric value cap (SPEC.md §1.4): a meter num/den, a `:N` beat count, and an ending number must
/// be `<= MAX_METER`. This bound also makes parsing panic-proof: a `[0-9]+` run can exceed
/// `u32::MAX` (e.g. `99999999999`), so we parse via `u64` and reject anything `> MAX_METER`
/// BEFORE narrowing to `u32` — `str::parse::<u32>().unwrap()` would otherwise panic on overflow.
pub const MAX_METER: u32 = 64;

/// Parse an ASCII-digit run, accepting it only if it is `<= MAX_METER`. Returns `None` on overflow
/// or over-cap (the caller emits the appropriate finding) — NEVER panics. `s` is already known to
/// be `[0-9]+` (it came from a digit-class regex capture).
fn parse_capped(s: &str) -> Option<u32> {
    match s.parse::<u64>() {
        Ok(n) if n <= MAX_METER as u64 => Some(n as u32),
        _ => None,
    }
}

const REQUIRED: [&str; 3] = ["title", "key", "time"];

fn meta_keys() -> &'static [&'static str] {
    &["title", "composer", "style", "key", "time"]
}

/// Section name -> neutral kind (SPEC.md §4.1). The iReal `*A` marker is the codec's job.
fn section_kind(name: &str) -> Option<SectionKind> {
    match name {
        "A" => Some(SectionKind::A),
        "B" => Some(SectionKind::B),
        "C" => Some(SectionKind::C),
        "D" => Some(SectionKind::D),
        "Intro" | "i" => Some(SectionKind::Intro),
        "Verse" | "v" => Some(SectionKind::Verse),
        _ => None,
    }
}

// --- compiled regexes (mirror the Python `re` patterns) ---------------------------------------

fn cell_re() -> &'static Regex {
    // re.findall(r"\([^)]*\)|\S+")
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"\([^)]*\)|\S+").unwrap())
}
fn inline_alt_re() -> &'static Regex {
    // "G7(Db7)" -> chord + (alt); ^([^(]+)(\([^)]*\))$
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"^([^(]+)(\([^)]*\))$").unwrap())
}
fn ending_re() -> &'static Regex {
    // ^([0-9]+)\.\s*([\s\S]*)$  (DOTALL via [\s\S]); ASCII digits only (SPEC.md §1.1).
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"^([0-9]+)\.\s*([\s\S]*)$").unwrap())
}
fn time_re() -> &'static Regex {
    // ^\[time:\s*([0-9]+)\s*/\s*([0-9]+)\s*\]\s*$  — `^`-ANCHORED so a `[time:…]`-shaped token can
    // only match a whole (pyStrip-ped) line, matching Python's re.match. ASCII digits (SPEC.md §1.1).
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"^\[time:\s*([0-9]+)\s*/\s*([0-9]+)\s*\]\s*$").unwrap())
}
fn section_re() -> &'static Regex {
    // ^\[([A-Za-z]+)([0-9]*)\]\s*$  — already `^`-anchored; ASCII digits only.
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"^\[([A-Za-z]+)([0-9]*)\]\s*$").unwrap())
}
fn header_re() -> &'static Regex {
    // ^([A-Za-z]+)\s*:\s*([\s\S]*)$  (value read literally to EOL)
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"^([A-Za-z]+)\s*:\s*([\s\S]*)$").unwrap())
}
fn header_time_re() -> &'static Regex {
    // ^([0-9]+)\s*/\s*([0-9]+)$  — ASCII digits only (SPEC.md §1.1).
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"^([0-9]+)\s*/\s*([0-9]+)$").unwrap())
}

// --- string helpers matching Python semantics -------------------------------------------------

/// Python str.strip(): strip ASCII + Unicode whitespace from both ends.
fn py_strip(s: &str) -> &str {
    s.trim()
}

/// Python str.rstrip(): strip trailing whitespace.
fn py_rstrip(s: &str) -> &str {
    s.trim_end()
}

/// Line split — the ONLY terminators are \r\n, \n, \r (SPEC.md §1.1). This is NOT Python's
/// str.splitlines() (which also breaks on \v \f \x1c \x1d \x1e \x85    ); the (now ASCII-pinned)
/// Python ref splits on this same three-form set, so all ports agree.
fn split_lines(text: &str) -> Vec<&str> {
    if text.is_empty() {
        return Vec::new();
    }
    let mut out: Vec<&str> = Vec::new();
    let bytes = text.as_bytes();
    let mut start = 0usize;
    let mut i = 0usize;
    while i < bytes.len() {
        let b = bytes[i];
        if b == b'\n' {
            out.push(&text[start..i]);
            i += 1;
            start = i;
        } else if b == b'\r' {
            out.push(&text[start..i]);
            if i + 1 < bytes.len() && bytes[i + 1] == b'\n' {
                i += 2;
            } else {
                i += 1;
            }
            start = i;
        } else {
            i += 1;
        }
    }
    // Python splitlines() does NOT yield a trailing empty string for a terminal newline; our
    // loop already only pushes when it hits a line boundary, so a remaining tail is real content.
    if start < bytes.len() {
        out.push(&text[start..]);
    }
    out
}

// --- internal node builders -------------------------------------------------------------------

fn make_measure(
    cells: Vec<Cell>,
    ending: Option<u32>,
    bar_open: bool,
    barline: Barline,
    line: u32,
) -> Measure {
    Measure {
        cells,
        ending,
        bar_open,
        barline,
        nav: Vec::new(),
        hints: Vec::new(),
        line,
    }
}

fn make_section(label: &str, kind: SectionKind) -> Section {
    Section {
        label: label.to_string(),
        kind,
        measures: Vec::new(),
    }
}

struct Findings {
    items: Vec<LintFinding>,
}

impl Findings {
    fn new() -> Self {
        Findings { items: Vec::new() }
    }
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

pub fn parse_dsl(text: &str) -> ParseResult {
    let mut f = Findings::new();

    if text.len() > MAX_BYTES {
        // text.len() is the UTF-8 byte length in Rust.
        f.err(0, "too-big", "input exceeds MAX_BYTES");
        return ParseResult {
            chart: None,
            findings: f.items,
        };
    }

    // Strip a leading BOM (Python text.lstrip("\u{feff}")).
    let text = text.trim_start_matches('\u{feff}');
    let lines = split_lines(text);
    if lines.len() > MAX_LINES {
        f.err(0, "too-big", "too many lines");
        return ParseResult {
            chart: None,
            findings: f.items,
        };
    }
    for (n, l) in lines.iter().enumerate() {
        // Python len() is by code point; MAX_LINE_LEN compares character count.
        if l.chars().count() > MAX_LINE_LEN {
            f.err((n + 1) as u32, "too-big", "line too long");
            return ParseResult {
                chart: None,
                findings: f.items,
            };
        }
    }

    let mut meta = Meta::new();
    let total = lines.len();
    let mut i = 0usize;

    // first-wins assign with duplicate/conflict findings
    fn assign_meta(meta: &mut Meta, f: &mut Findings, k: &str, v: MetaValue, lineno: u32) {
        if meta.contains(k) {
            let same = meta.get(k) == Some(&v);
            if same {
                f.warn(
                    lineno,
                    "duplicate-header",
                    &format!("duplicate header '{}'", k),
                );
            } else {
                f.err(
                    lineno,
                    "conflicting-header",
                    &format!("conflicting header '{}'", k),
                );
            }
            return;
        }
        meta.insert(k, v);
    }

    // --- header ---
    while i < total {
        let raw = lines[i];
        let line = py_strip(raw);
        if line.is_empty() || line.starts_with('#') {
            i += 1;
            continue;
        }
        let first = line.chars().next();
        if matches!(first, Some('[') | Some('|') | Some('{')) {
            break;
        }
        let caps = match header_re().captures(raw) {
            Some(c) => c,
            None => break,
        };
        let key = caps.get(1).unwrap().as_str().to_lowercase();
        let val = py_rstrip(caps.get(2).unwrap().as_str());
        if val.contains('=') {
            f.err(
                (i + 1) as u32,
                "meta-delimiter",
                &format!("'=' not allowed in metadata value: {}", val),
            );
        }
        if key == "time" {
            // checked parse + MAX_METER cap (SPEC.md §1.4): never .unwrap() a u32 parse — a long
            // digit run overflows u32 and would panic. parse_capped returns None on overflow/cap.
            let parsed = header_time_re().captures(val).and_then(|tm| {
                let n = parse_capped(tm.get(1).unwrap().as_str())?;
                let d = parse_capped(tm.get(2).unwrap().as_str())?;
                Some((n, d))
            });
            if let Some((n, d)) = parsed {
                assign_meta(
                    &mut meta,
                    &mut f,
                    "time",
                    MetaValue::Time((n, d)),
                    (i + 1) as u32,
                );
            } else {
                f.err(
                    (i + 1) as u32,
                    "bad-time",
                    &format!("bad time signature: {}", val),
                );
            }
        } else if meta_keys().contains(&key.as_str()) {
            assign_meta(
                &mut meta,
                &mut f,
                &key,
                MetaValue::Str(val.to_string()),
                (i + 1) as u32,
            );
        } else {
            f.warn(
                (i + 1) as u32,
                "unknown-key",
                &format!("unknown header key: {}", key),
            );
        }
        i += 1;
    }

    for k in REQUIRED {
        if !meta.contains(k) {
            f.err(
                0,
                "missing-header",
                &format!("missing required header: {}", k),
            );
        }
    }
    if meta.get_str("title").unwrap_or("").is_empty() {
        f.err(0, "missing-header", "title must be non-empty");
    }

    // --- body ---
    let mut sections: Vec<Section> = Vec::new();
    let mut cur: Option<usize> = None; // index into `sections`
    let mut pending_nav: Vec<NavItem> = Vec::new();
    let mut pending_hints: Vec<String> = Vec::new();
    let mut measure_count = 0usize;
    let mut current_time: Time = meta.get_time("time").unwrap_or((4, 4));

    while i < total {
        let raw = lines[i];
        let line = py_strip(raw);
        let ln = (i + 1) as u32;
        i += 1;
        if line.is_empty() || line.starts_with('#') {
            continue;
        }

        // [time: n/d]
        if line.starts_with("[time") {
            if let Some(tm) = time_re().captures(line) {
                // checked parse + MAX_METER cap (SPEC.md §1.4/§4.4): recognized shape but an
                // out-of-range/overflowing meter is a bad-time error (and contributes no nav).
                let n = parse_capped(tm.get(1).unwrap().as_str());
                let d = parse_capped(tm.get(2).unwrap().as_str());
                match (n, d) {
                    (Some(n), Some(d)) => {
                        let newt: Time = (n, d);
                        if newt == current_time {
                            f.warn(
                                ln,
                                "redundant-time",
                                &format!("[time: {}/{}] repeats the current meter", n, d),
                            );
                        }
                        current_time = newt;
                        pending_nav.push(NavItem::Time(newt));
                    }
                    _ => {
                        f.err(ln, "bad-time", "meter component exceeds MAX_METER");
                    }
                }
                continue;
            }
        }

        // [Section]
        if let Some(sec) = section_re().captures(line) {
            let name = sec.get(1).unwrap().as_str();
            let suffix = sec.get(2).unwrap().as_str();
            let kind = match section_kind(name) {
                Some(k) => k,
                None => {
                    f.err(
                        ln,
                        "unknown-section",
                        &format!("unknown section '{}'; allowed: A-D, Intro, Verse", name),
                    );
                    SectionKind::A
                }
            };
            sections.push(make_section(&format!("{}{}", name, suffix), kind));
            cur = Some(sections.len() - 1);
            continue;
        }

        // @directive
        if line.starts_with('@') {
            if line.contains("segno") {
                pending_nav.push(NavItem::Segno);
            } else if line.contains("tocoda")
                || line.contains("to coda")
                || line.contains("to-coda")
            {
                // "To Coda" jump-point: a Q AFTER the PRECEDING measure's chords (not the next).
                // Checked before "coda" because the word "tocoda" contains "coda".
                let attached = match cur {
                    Some(ci) if !sections[ci].measures.is_empty() => {
                        let last = sections[ci].measures.last_mut().unwrap();
                        last.nav.push(NavItem::Tocoda);
                        true
                    }
                    _ => false,
                };
                if !attached {
                    f.warn(
                        ln,
                        "tocoda-without-measure",
                        "@tocoda has no preceding measure",
                    );
                }
            } else if line.contains("fine") {
                pending_nav.push(NavItem::Fine);
            } else if line.contains("coda") {
                pending_nav.push(NavItem::Coda);
            } else if line.contains("break") || line.contains("newline") {
                // iReal page-layout only — NO lead-sheet semantics. Demoted to an opaque
                // render-hint (Phase 2 §3.3); the codec reads it, the text target ignores it.
                pending_hints.push("break".to_string());
            } else {
                f.warn(ln, "unknown-nav", &format!("unknown @directive: {}", line));
            }
            continue;
        }

        // <text>
        if line.starts_with('<') && line.ends_with('>') {
            pending_nav.push(NavItem::Text(line.to_string()));
            continue;
        }

        // otherwise: a measure line
        if cur.is_none() {
            sections.push(make_section("A", SectionKind::A));
            cur = Some(sections.len() - 1);
        }
        let ci = cur.unwrap();
        let measures = parse_measure_line(line, ln, &mut f);
        for mut m in measures {
            if !pending_nav.is_empty() {
                let mut nav = std::mem::take(&mut pending_nav);
                nav.append(&mut m.nav);
                m.nav = nav;
            }
            if !pending_hints.is_empty() {
                let mut hints = std::mem::take(&mut pending_hints);
                hints.append(&mut m.hints);
                m.hints = hints;
            }
            sections[ci].measures.push(m);
            measure_count += 1;
            if measure_count > MAX_MEASURES {
                f.err(ln, "too-big", "too many measures");
                return ParseResult {
                    chart: Some(LeadSheet { meta, sections }),
                    findings: f.items,
                };
            }
        }
    }

    if sections.is_empty() || sections.iter().all(|s| s.measures.is_empty()) {
        f.err(0, "empty-chart", "no sections or measures");
    }

    ParseResult {
        chart: Some(LeadSheet { meta, sections }),
        findings: f.items,
    }
}

/// Python re.split with a capturing group, e.g. re.split(r"(\{|\}|\|\||\||Z)", line) — the
/// delimiters are retained as their own elements. Implemented by hand (the Rust `regex` crate's
/// `split` discards delimiters). Longest-match-first ordering matches the alternation: `||`
/// before `|`.
fn split_with_barlines(line: &str) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    let bytes = line.as_bytes();
    let mut start = 0usize;
    let mut i = 0usize;
    while i < bytes.len() {
        let b = bytes[i];
        let (delim, dlen): (Option<&str>, usize) = match b {
            b'{' => (Some("{"), 1),
            b'}' => (Some("}"), 1),
            b'Z' => (Some("Z"), 1),
            b'|' => {
                if i + 1 < bytes.len() && bytes[i + 1] == b'|' {
                    (Some("||"), 2)
                } else {
                    (Some("|"), 1)
                }
            }
            _ => (None, 0),
        };
        if let Some(d) = delim {
            out.push(line[start..i].to_string());
            out.push(d.to_string());
            i += dlen;
            start = i;
        } else {
            i += 1;
        }
    }
    out.push(line[start..].to_string());
    out
}

fn parse_measure_line(line: &str, ln: u32, f: &mut Findings) -> Vec<Measure> {
    let parts = split_with_barlines(line);
    let mut measures: Vec<Measure> = Vec::new();
    let mut bar_open = false;
    let mut buf: Option<String> = None;
    for p in parts {
        if p == "{" {
            bar_open = true;
            continue;
        }
        if p == "|" || p == "}" || p == "||" || p == "Z" {
            let buf_nonempty = buf
                .as_deref()
                .map(|b| !py_strip(b).is_empty())
                .unwrap_or(false);
            if buf_nonempty {
                let close = if p == "||" || p == "Z" {
                    Barline::Final
                } else if p == "}" {
                    Barline::RepeatEnd
                } else {
                    Barline::Normal
                };
                let (ending, cells) = parse_cells(buf.as_deref().unwrap(), ln, f);
                measures.push(make_measure(cells, ending, bar_open, close, ln));
                bar_open = false;
            } else if p == "}" && !measures.is_empty() {
                measures.last_mut().unwrap().barline = Barline::RepeatEnd;
            }
            buf = None;
            continue;
        }
        if !py_strip(&p).is_empty() {
            buf = Some(p);
        }
    }
    if let Some(b) = &buf {
        if !py_strip(b).is_empty() {
            let (ending, cells) = parse_cells(b, ln, f);
            measures.push(make_measure(cells, ending, bar_open, Barline::Normal, ln));
        }
    }
    measures
}

fn parse_cells(content: &str, ln: u32, f: &mut Findings) -> (Option<u32>, Vec<Cell>) {
    let mut content = py_strip(content).to_string();
    let mut ending: Option<u32> = None;
    if let Some(m) = ending_re().captures(&content) {
        let raw_ending = m.get(1).unwrap().as_str();
        match parse_capped(raw_ending) {
            // an ending number > MAX_METER (SPEC.md §1.4) is a typo and would overflow u32 on a
            // naive .parse().unwrap(); reject with the generic size-cap code, never panic.
            Some(n) => ending = Some(n),
            None => f.err(
                ln,
                "too-big",
                &format!("ending number exceeds MAX_METER: {}", raw_ending),
            ),
        }
        content = py_strip(m.get(2).unwrap().as_str()).to_string();
    }
    let mut cells: Vec<Cell> = Vec::new();
    for tok in find_all_cells(&content) {
        if tok.starts_with('(') {
            if count_tokens(&strip_parens(&tok)) > MAX_ALT_CHORD_TOKENS {
                f.err(ln, "alt-too-long", "alt chord has too many tokens");
            }
            if let Some(last) = cells.last_mut() {
                last.alt = Some(tok.clone());
            } else {
                f.warn(
                    ln,
                    "alt-without-chord",
                    &format!("alt group {} has no preceding chord", tok),
                );
            }
            continue;
        }
        // Split an inline alt off the chord, e.g. "G7(Db7)" -> chord "G7" + alt "(Db7)".
        let mut chord_tok = tok.clone();
        let mut inline_alt: Option<String> = None;
        if let Some(am) = inline_alt_re().captures(&tok) {
            chord_tok = am.get(1).unwrap().as_str().to_string();
            let alt = am.get(2).unwrap().as_str().to_string();
            if count_tokens(&strip_parens(&alt)) > MAX_ALT_CHORD_TOKENS {
                f.err(ln, "alt-too-long", "alt chord has too many tokens");
            }
            inline_alt = Some(alt);
        }
        let mut chord = chord_tok.clone();
        let mut beats: Option<u32> = None;
        if let Some(idx) = chord_tok.find(':') {
            // Python str.partition(":"): split at the FIRST ":".
            chord = chord_tok[..idx].to_string();
            let b = &chord_tok[idx + 1..];
            if is_digits(b) {
                // checked parse + MAX_METER cap (SPEC.md §1.4): a long digit run overflows u32, so
                // parse_capped returns None instead of panicking; over-cap is a bad-beats error.
                match parse_capped(b) {
                    Some(n) => beats = Some(n),
                    None => f.err(
                        ln,
                        "bad-beats",
                        &format!("beat count exceeds MAX_METER in {}", chord_tok),
                    ),
                }
            } else {
                f.err(
                    ln,
                    "bad-beats",
                    &format!("bad beat count in {} (expected :<digits>)", chord_tok),
                );
            }
        }
        if chord.chars().count() > MAX_CHORD_TOKEN_LEN {
            let preview: String = chord.chars().take(20).collect();
            f.err(
                ln,
                "token-too-long",
                &format!("chord token too long: {}…", preview),
            );
        }
        cells.push(Cell {
            chord,
            beats,
            alt: inline_alt,
        });
        if cells.len() > MAX_CELLS_PER_MEASURE {
            f.err(ln, "too-big", "too many cells in a measure");
            break;
        }
    }
    (ending, cells)
}

/// Python re.findall(r"\([^)]*\)|\S+", content).
fn find_all_cells(content: &str) -> Vec<String> {
    cell_re()
        .find_iter(content)
        .map(|m| m.as_str().to_string())
        .collect()
}

/// Python tok.strip("()"): strip leading/trailing '(' and ')' characters.
fn strip_parens(s: &str) -> String {
    s.trim_matches(|c| c == '(' || c == ')').to_string()
}

/// Count whitespace-separated non-empty tokens (Python `s.split()` length).
fn count_tokens(s: &str) -> usize {
    s.split_whitespace().count()
}

/// Python str.isdigit() for the ASCII-digit case used here (non-empty, all 0-9).
fn is_digits(s: &str) -> bool {
    !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit())
}
