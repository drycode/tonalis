/**
 * Bounded, single-pass DSL parser (SPEC.md §1–§4). Never throws on arbitrary input; limit
 * violations and structural problems become findings. The parser records structure; the linter
 * (lint.ts) judges chord validity, beat sums, etc. Header values are read literally to EOL.
 *
 * Faithful port of the Python `parser.py` reference.
 */

import type {
  Barline,
  Cell,
  LeadSheet,
  LintFinding,
  Measure,
  NavItem,
  ParseResult,
  Section,
  SectionKind,
  Severity,
  Time,
} from "./ast.js";

export const MAX_BYTES = 256 * 1024;
export const MAX_LINES = 5000;
export const MAX_LINE_LEN = 1000;
export const MAX_MEASURES = 2000;
export const MAX_CELLS_PER_MEASURE = 16;
export const MAX_CHORD_TOKEN_LEN = 50;
export const MAX_ALT_CHORD_TOKENS = 8;
// Numeric value cap (SPEC.md §1.4): a meter num/den, a :N beat count, and an ending number must
// be <= MAX_METER. Exceeding it never reaches rendering, so it can't drive a giant " ".repeat().
export const MAX_METER = 64;

const REQUIRED = ["title", "key", "time"] as const;
const META_KEYS = new Set(["title", "composer", "style", "key", "time"]);
const SECTIONS: Record<string, SectionKind> = {
  A: "a",
  B: "b",
  C: "c",
  D: "d",
  Intro: "intro",
  i: "intro",
  Verse: "verse",
  v: "verse",
};

// Mirror the Python `re` patterns. The barline regex is used with a *capturing* split so the
// delimiters are retained in the result array (Python's re.split with a captured group).
const BARLINE_RE = /(\{|\}|\|\||\||Z)/;
const CELL_RE = /\([^)]*\)|\S+/g; // a (alt) group, or a non-space run
const INLINE_ALT_RE = /^([^(]+)(\([^)]*\))$/; // "G7(Db7)" -> chord + (alt)
const ENDING_RE = /^([0-9]+)\.\s*([\s\S]*)$/; // ending number + rest (DOTALL via [\s\S])
// `^`-ANCHORED: JS .test/.exec is unanchored, so an UNanchored TIME_RE/SECTION_RE would match a
// `[B]`-shaped token mid-measure (e.g. `C7 | F7 | C7 [B]`) and silently treat the line as a
// section, dropping every chord. The `^` (the line is already pyStrip-ped) forces a whole-line
// match, exactly like Python's re.match. ASCII digits only ([0-9], not \d) per SPEC.md §1.1.
const TIME_RE = /^\[time:\s*([0-9]+)\s*\/\s*([0-9]+)\s*\]\s*$/;
const SECTION_RE = /^\[([A-Za-z]+)([0-9]*)\]\s*$/;
const HEADER_RE = /^([A-Za-z]+)\s*:\s*([\s\S]*)$/; // value read literally to EOL
const HEADER_TIME_RE = /^([0-9]+)\s*\/\s*([0-9]+)$/;

// --- string helpers matching Python semantics -------------------------------------------------

/** Python str.strip(): strip ASCII + Unicode whitespace from both ends. */
function pyStrip(s: string): string {
  return s.replace(/^\s+/u, "").replace(/\s+$/u, "");
}

/** Python str.rstrip(): strip trailing whitespace. */
function pyRstrip(s: string): string {
  return s.replace(/\s+$/u, "");
}

/**
 * Line split — the ONLY terminators are `\r\n`, `\n`, `\r` (SPEC.md §1.1). The Python reference
 * splits on this same three-form set (NOT str.splitlines(), which would also break on
 * \v \f \x1c \x1d \x1e \x85    ); those Unicode line boundaries are ordinary characters here,
 * so all three ports split identically.
 */
function splitLines(text: string): string[] {
  if (text === "") return [];
  // Split on the three ASCII newline forms. Use a regex that consumes \r\n as one boundary.
  const parts = text.split(/\r\n|\r|\n/);
  // Python splitlines() does NOT yield a trailing empty string for a terminal newline.
  if (parts.length > 0 && parts[parts.length - 1] === "") {
    // Only drop the final empty element if the text ended with a newline.
    if (/(\r\n|\r|\n)$/.test(text)) parts.pop();
  }
  return parts;
}

/** Number of UTF-8 bytes in a string, matching len(text.encode("utf-8")). */
function utf8ByteLength(s: string): number {
  if (typeof TextEncoder !== "undefined") return new TextEncoder().encode(s).length;
  let n = 0;
  for (let i = 0; i < s.length; i++) {
    let code = s.charCodeAt(i);
    if (code >= 0xd800 && code <= 0xdbff && i + 1 < s.length) {
      const next = s.charCodeAt(i + 1);
      if (next >= 0xdc00 && next <= 0xdfff) {
        code = 0x10000 + ((code - 0xd800) << 10) + (next - 0xdc00);
        i++;
      }
    }
    if (code < 0x80) n += 1;
    else if (code < 0x800) n += 2;
    else if (code < 0x10000) n += 3;
    else n += 4;
  }
  return n;
}

// --- mutable internal node builders (the dataclasses) -----------------------------------------

function makeCell(chord: string, beats: number | null, alt: string | null): Cell {
  return { chord, beats, alt };
}

function makeMeasure(opts: Partial<Measure> & { line: number }): Measure {
  return {
    cells: opts.cells ?? [],
    ending: opts.ending ?? null,
    bar_open: opts.bar_open ?? false,
    barline: opts.barline ?? "normal",
    nav: opts.nav ?? [],
    hints: opts.hints ?? [],
    line: opts.line,
  };
}

function makeSection(label: string, kind: SectionKind): Section {
  return { label, kind, measures: [] };
}

type Emit = (line: number, code: string, msg: string) => void;

export function parseDsl(text: string): ParseResult {
  const findings: LintFinding[] = [];
  const push = (severity: Severity, line: number, code: string, msg: string): void => {
    findings.push({ severity, line, code, message: msg });
  };
  const err: Emit = (line, code, msg) => push("error", line, code, msg);
  const warn: Emit = (line, code, msg) => push("warning", line, code, msg);

  if (utf8ByteLength(text) > MAX_BYTES) {
    err(0, "too-big", "input exceeds MAX_BYTES");
    return { chart: null, findings };
  }
  // Strip a leading BOM (Python text.lstrip("﻿")).
  text = text.replace(/^﻿+/, "");
  const lines = splitLines(text);
  if (lines.length > MAX_LINES) {
    err(0, "too-big", "too many lines");
    return { chart: null, findings };
  }
  for (let n = 0; n < lines.length; n++) {
    // Count CODE POINTS, not UTF-16 units: Python uses len() and Rust uses chars().count() (both
    // code-point counts), so a line of astral chars must be capped identically across ports.
    if ([...lines[n]!].length > MAX_LINE_LEN) {
      err(n + 1, "too-big", "line too long");
      return { chart: null, findings };
    }
  }

  const meta: Record<string, string | Time> = {};
  let i = 0;
  const total = lines.length;

  function assignMeta(k: string, v: string | Time, lineno: number): void {
    // Header keys are singletons. Re-stating one is a duplicate (same value) or a conflict
    // (different value) — never silently last-wins. Keep the first value.
    if (k in meta) {
      const existing = meta[k]!;
      const same = Array.isArray(existing)
        ? Array.isArray(v) && existing[0] === v[0] && existing[1] === v[1]
        : existing === v;
      if (same) {
        warn(lineno, "duplicate-header", `duplicate header '${k}'`);
      } else {
        err(lineno, "conflicting-header", `conflicting header '${k}'`);
      }
      return;
    }
    meta[k] = v;
  }

  // --- header ---
  while (i < total) {
    const raw = lines[i]!;
    const line = pyStrip(raw);
    if (line === "" || line.startsWith("#")) {
      i += 1;
      continue;
    }
    if (line[0] === "[" || line[0] === "|" || line[0] === "{") break;
    const m = HEADER_RE.exec(raw); // value read literally to EOL
    if (!m) break;
    const key = m[1]!.toLowerCase();
    const val = pyRstrip(m[2]!);
    if (val.includes("=")) {
      err(i + 1, "meta-delimiter", `'=' not allowed in metadata value: ${val}`);
    }
    if (key === "time") {
      const tm = HEADER_TIME_RE.exec(val);
      // both meter components must be <= MAX_METER (SPEC.md §1.4).
      const n = tm ? parseInt(tm[1]!, 10) : 0;
      const d = tm ? parseInt(tm[2]!, 10) : 0;
      if (tm && n <= MAX_METER && d <= MAX_METER) {
        assignMeta("time", [n, d], i + 1);
      } else {
        err(i + 1, "bad-time", `bad time signature: ${val}`);
      }
    } else if (META_KEYS.has(key)) {
      assignMeta(key, val, i + 1);
    } else {
      warn(i + 1, "unknown-key", `unknown header key: ${key}`);
    }
    i += 1;
  }

  for (const k of REQUIRED) {
    if (!(k in meta)) err(0, "missing-header", `missing required header: ${k}`);
  }
  if ((meta["title"] ?? "") === "") {
    err(0, "missing-header", "title must be non-empty");
  }

  // --- body ---
  const sections: Section[] = [];
  let cur: Section | null = null;
  let pendingNav: NavItem[] = [];
  let pendingHints: string[] = [];
  let measureCount = 0;
  let currentTime: Time = (meta["time"] as Time) ?? [4, 4];

  function ensureSection(): Section {
    if (cur === null) {
      cur = makeSection("A", "a");
      sections.push(cur);
    }
    return cur;
  }

  while (i < total) {
    const raw = lines[i]!;
    const line = pyStrip(raw);
    const ln = i + 1;
    i += 1;
    if (line === "" || line.startsWith("#")) continue;

    const tm = TIME_RE.exec(line);
    if (line.startsWith("[time") && tm) {
      const n = parseInt(tm[1]!, 10);
      const d = parseInt(tm[2]!, 10);
      if (n > MAX_METER || d > MAX_METER) {
        // recognized [time:…] shape but the meter is out of range (SPEC.md §1.4/§4.4).
        err(ln, "bad-time", `meter component exceeds MAX_METER: ${n}/${d}`);
        continue;
      }
      const newt: Time = [n, d];
      if (newt[0] === currentTime[0] && newt[1] === currentTime[1]) {
        warn(ln, "redundant-time", `[time: ${newt[0]}/${newt[1]}] repeats the current meter`);
      }
      currentTime = newt;
      pendingNav.push(["time", newt]);
      continue;
    }

    const sec = SECTION_RE.exec(line);
    if (sec) {
      const name = sec[1]!;
      let kind = SECTIONS[name];
      if (kind === undefined) {
        err(ln, "unknown-section", `unknown section '${name}'; allowed: A-D, Intro, Verse`);
        kind = "a";
      }
      cur = makeSection(name + sec[2]!, kind);
      sections.push(cur);
      continue;
    }

    if (line.startsWith("@")) {
      if (line.includes("segno")) {
        pendingNav.push(["segno"]);
      } else if (
        line.includes("tocoda") ||
        line.includes("to coda") ||
        line.includes("to-coda")
      ) {
        // "To Coda" jump-point: a Q AFTER the PRECEDING measure's chords (not the next one).
        // Checked before "coda" because the word "tocoda" contains "coda".
        if (cur !== null && cur.measures.length > 0) {
          const last = cur.measures[cur.measures.length - 1]!;
          last.nav = [...last.nav, ["tocoda"]];
        } else {
          warn(ln, "tocoda-without-measure", "@tocoda has no preceding measure");
        }
      } else if (line.includes("fine")) {
        pendingNav.push(["fine"]);
      } else if (line.includes("coda")) {
        pendingNav.push(["coda"]);
      } else if (line.includes("break") || line.includes("newline")) {
        // page-layout only — NO lead-sheet semantics. Demoted to an opaque render-hint
        // (Phase 2 §3.3); a downstream codec reads it, the text-target ignores it.
        pendingHints.push("break");
      } else {
        warn(ln, "unknown-nav", `unknown @directive: ${line}`);
      }
      continue;
    }

    if (line.startsWith("<") && line.endsWith(">")) {
      pendingNav.push(["text", line]);
      continue;
    }

    // otherwise: a measure line
    const section = ensureSection();
    const measures = parseMeasureLine(line, ln, err, warn);
    for (const m of measures) {
      if (pendingNav.length > 0) {
        m.nav = [...pendingNav, ...m.nav];
        pendingNav = [];
      }
      if (pendingHints.length > 0) {
        m.hints = [...pendingHints, ...m.hints];
        pendingHints = [];
      }
      section.measures.push(m);
      measureCount += 1;
      if (measureCount > MAX_MEASURES) {
        err(ln, "too-big", "too many measures");
        return { chart: { meta: meta as LeadSheet["meta"], sections }, findings };
      }
    }
  }

  if (sections.length === 0 || sections.every((s) => s.measures.length === 0)) {
    err(0, "empty-chart", "no sections or measures");
  }
  return { chart: { meta: meta as LeadSheet["meta"], sections }, findings };
}

/**
 * Python re.split with a capturing group, e.g. re.split(r"(\{|\}|\|\||\||Z)", line).
 * JS String.split with a capturing group has the same retain-delimiters semantics.
 */
function splitWithBarlines(line: string): string[] {
  return line.split(BARLINE_RE);
}

function parseMeasureLine(line: string, ln: number, err: Emit, warn: Emit): Measure[] {
  const parts = splitWithBarlines(line);
  const measures: Measure[] = [];
  let barOpen = false;
  let buf: string | null = null;
  for (const p of parts) {
    if (p === "{") {
      barOpen = true;
      continue;
    }
    if (p === "|" || p === "}" || p === "||" || p === "Z") {
      if (buf !== null && pyStrip(buf) !== "") {
        const close: Barline =
          p === "||" || p === "Z" ? "final" : p === "}" ? "repeat_end" : "normal";
        const [ending, cells] = parseCells(buf, ln, err, warn);
        measures.push(
          makeMeasure({ cells, ending, bar_open: barOpen, barline: close, line: ln }),
        );
        barOpen = false;
      } else if (p === "}" && measures.length > 0) {
        measures[measures.length - 1]!.barline = "repeat_end";
      }
      buf = null;
      continue;
    }
    if (pyStrip(p) !== "") {
      buf = p;
    }
  }
  if (buf !== null && pyStrip(buf) !== "") {
    const [ending, cells] = parseCells(buf, ln, err, warn);
    measures.push(makeMeasure({ cells, ending, bar_open: barOpen, barline: "normal", line: ln }));
  }
  return measures;
}

function parseCells(
  content: string,
  ln: number,
  err: Emit,
  warn: Emit,
): [number | null, Cell[]] {
  content = pyStrip(content);
  let ending: number | null = null;
  const m = ENDING_RE.exec(content);
  if (m) {
    ending = parseInt(m[1]!, 10);
    content = pyStrip(m[2]!);
    // an ending number > MAX_METER (SPEC.md §1.4) is a typo and would overflow downstream ports.
    if (ending > MAX_METER) {
      err(ln, "too-big", `ending number exceeds MAX_METER: ${ending}`);
    }
  }
  const cells: Cell[] = [];
  for (const tok of findAllCells(content)) {
    if (tok.startsWith("(")) {
      if (stripParens(tok).split(/\s+/).filter(Boolean).length > MAX_ALT_CHORD_TOKENS) {
        err(ln, "alt-too-long", "alt chord has too many tokens");
      }
      if (cells.length > 0) {
        cells[cells.length - 1]!.alt = tok;
      } else {
        warn(ln, "alt-without-chord", `alt group ${tok} has no preceding chord`);
      }
      continue;
    }
    // Split an inline alt off the chord, e.g. "G7(Db7)" -> chord "G7" + alt "(Db7)".
    let chordTok = tok;
    let inlineAlt: string | null = null;
    const am = INLINE_ALT_RE.exec(tok);
    if (am) {
      chordTok = am[1]!;
      inlineAlt = am[2]!;
      if (stripParens(inlineAlt).split(/\s+/).filter(Boolean).length > MAX_ALT_CHORD_TOKENS) {
        err(ln, "alt-too-long", "alt chord has too many tokens");
      }
    }
    let chord = chordTok;
    let beats: number | null = null;
    if (chordTok.includes(":")) {
      // Python str.partition(":"): split at the FIRST ":".
      const idx = chordTok.indexOf(":");
      chord = chordTok.slice(0, idx);
      const b = chordTok.slice(idx + 1);
      if (isDigits(b)) {
        const n = parseInt(b, 10);
        if (n > MAX_METER) {
          err(ln, "bad-beats", `beat count exceeds MAX_METER in ${chordTok}`);
        } else {
          beats = n;
        }
      } else {
        err(ln, "bad-beats", `bad beat count in ${chordTok} (expected :<digits>)`);
      }
    }
    // Count CODE POINTS (not UTF-16 units) to match Python len() / Rust chars().count().
    if ([...chord].length > MAX_CHORD_TOKEN_LEN) {
      err(ln, "token-too-long", `chord token too long: ${chord.slice(0, 20)}…`);
    }
    cells.push(makeCell(chord, beats, inlineAlt));
    if (cells.length > MAX_CELLS_PER_MEASURE) {
      err(ln, "too-big", "too many cells in a measure");
      break;
    }
  }
  return [ending, cells];
}

/** Python re.findall(r"\([^)]*\)|\S+", content). */
function findAllCells(content: string): string[] {
  const out: string[] = [];
  CELL_RE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = CELL_RE.exec(content)) !== null) {
    out.push(m[0]);
    if (m.index === CELL_RE.lastIndex) CELL_RE.lastIndex++; // guard against zero-width
  }
  return out;
}

/** Python tok.strip("()"): strip leading/trailing '(' and ')' characters. */
function stripParens(s: string): string {
  return s.replace(/^[()]+/, "").replace(/[()]+$/, "");
}

/** Python str.isdigit() for the ASCII-digit case used here (non-empty, all 0-9). */
function isDigits(s: string): boolean {
  return s.length > 0 && /^[0-9]+$/.test(s);
}
