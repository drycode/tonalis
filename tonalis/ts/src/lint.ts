/**
 * DSL linter: structural + chord-grammar checks over a parsed DslChart (SPEC.md §3–§5).
 * Errors block compilation; warnings don't. Uses the music_dsl-backed chord validator (chords.ts).
 *
 * Faithful port of the Python `lint.py` reference.
 */

import type { LeadSheet, LintFinding, Measure, NavItem, Section, Severity } from "./ast.js";
import { isValidChord } from "./chords.js";
import { MAX_CHORD_TOKEN_LEN } from "./parser.js";

// corpus-derived known-good uneven :N layouts (4/4); all-equal splits are always fine.
const ALLOWED_UNEVEN: ReadonlySet<string> = new Set(
  [
    [2, 1, 1],
    [1, 1, 1, 1],
    [1, 1, 2],
    [3, 1],
    [1, 3],
    [2, 2],
  ].map((t) => t.join(",")),
);

function allMeasures(chart: LeadSheet): Array<[Section, Measure]> {
  const out: Array<[Section, Measure]> = [];
  for (const s of chart.sections) for (const m of s.measures) out.push([s, m]);
  return out;
}

/**
 * Per-cell beat counts: explicit :N consume their count; unannotated split the remainder
 * evenly. Returns [pattern, ok] where ok is false if the bar can't be filled.
 */
function beatPattern(measure: Measure, numerator: number): [number[], boolean] {
  const cells = measure.cells;
  if (cells.length === 0) return [[], true];
  let explicit = 0;
  for (const c of cells) if (c.beats) explicit += c.beats;
  const unannotated = cells.filter((c) => !c.beats);
  const remainder = numerator - explicit;
  if (unannotated.length > 0) {
    if (remainder <= 0 || remainder % unannotated.length !== 0) {
      return [cells.map((c) => c.beats ?? 0), false];
    }
    const each = Math.trunc(remainder / unannotated.length);
    return [cells.map((c) => (c.beats ? c.beats : each)), true];
  }
  // all explicit
  return [cells.map((c) => c.beats as number), explicit === numerator];
}

function navEquals(nav: NavItem, ...atoms: string[]): boolean {
  return nav.length === atoms.length && nav.every((a, idx) => a === atoms[idx]);
}

export function lint(chart: LeadSheet): LintFinding[] {
  const findings: LintFinding[] = [];
  const push = (severity: Severity, line: number, code: string, msg: string): void => {
    findings.push({ severity, line, code, message: msg });
  };
  const err = (line: number, code: string, msg: string): void => push("error", line, code, msg);
  const warn = (line: number, code: string, msg: string): void =>
    push("warning", line, code, msg);

  const measures = allMeasures(chart);
  let numerator = (chart.meta.time ?? [4, 4])[0];

  // repeats / endings balance, codas/segno, final bar, per-measure beats + chords
  let balance = 0;
  let nCoda = 0;
  let nSegno = 0;
  const lastIdx = measures.length - 1;

  for (let idx = 0; idx < measures.length; idx++) {
    const m = measures[idx]![1];
    for (const nav of m.nav) {
      if (navEquals(nav, "coda")) nCoda += 1;
      else if (navEquals(nav, "segno")) nSegno += 1;
      else if (nav.length > 0 && nav[0] === "time") numerator = (nav[1] as [number, number])[0];
    }
    if (m.bar_open) balance += 1;
    if (m.barline === "repeat_end") {
      if (balance === 0) err(m.line, "unbalanced-repeat", "'}' with no matching '{'");
      else balance -= 1;
    }
    if (m.barline === "final" && idx !== lastIdx) {
      warn(m.line, "mid-final-bar", "final barline (Z/||) is not on the last measure");
    }

    // chords
    for (const c of m.cells) {
      // skip is_valid_chord for tokens that already triggered token-too-long (parser error already
      // emitted; music_dsl would reject them as bad-chord too but the conformance spec treats
      // over-length tokens as a single token-too-long error). Mirrors Python lint.py:79.
      if (c.chord && [...c.chord].length <= MAX_CHORD_TOKEN_LEN && !isValidChord(c.chord)) {
        err(m.line, "bad-chord", `invalid chord token: ${c.chord}`);
      }
      if (c.alt) {
        for (const tok of stripParens(c.alt).split(/\s+/).filter(Boolean)) {
          if (!isValidChord(tok)) err(m.line, "bad-chord", `invalid alt chord: ${tok}`);
        }
      }
    }

    // empty measure
    if (m.cells.length === 0) {
      warn(m.line, "empty-measure", "measure has no chords (emitted as N.C.)");
      continue;
    }

    // beats. Pickup relaxation only excuses an UNDER-full first/last bar (anacrusis); an
    // OVER-full bar is always wrong, even for a pickup.
    const [pattern, ok] = beatPattern(m, numerator);
    const total = pattern.reduce((a, b) => a + b, 0);
    const isPickup = idx === 0 || idx === lastIdx;
    if (total > numerator) {
      err(m.line, "beat-sum", `beats ${fmt(pattern)} overflow a ${numerator}-beat bar`);
    } else if (!ok && !isPickup) {
      err(m.line, "beat-sum", `beats ${fmt(pattern)} do not fill a ${numerator}-beat bar`);
    } else if (ok && new Set(pattern).size > 1 && !ALLOWED_UNEVEN.has(pattern.join(","))) {
      warn(
        m.line,
        "beat-unsupported",
        `uneven beat layout ${fmt(pattern)} not in the allowlist; even-split fallback`,
      );
    }
  }

  if (balance !== 0) err(0, "unbalanced-repeat", `${balance} unclosed '{'`);

  // an empty section (header but no measures) silently drops in render — surface it
  for (const section of chart.sections) {
    if (section.measures.length === 0) {
      warn(0, "empty-section", `section [${section.label}] has no measures (dropped)`);
    }
  }

  // nth endings must belong to a repeat (a section with endings needs a bar_open)
  for (const section of chart.sections) {
    const hasOpen = section.measures.some((m) => m.bar_open);
    if (section.measures.some((m) => m.ending) && !hasOpen) {
      const first = section.measures.find((m) => m.ending);
      const ln = first ? first.line : 0;
      err(ln, "ending-without-repeat", "nth ending outside a repeat block");
    }
  }

  if (nCoda > 2) {
    err(0, "coda-count", `${nCoda} coda points (max 2 — the encoder cannot flatten more)`);
  } else if (nCoda === 2 && nSegno === 0) {
    warn(0, "coda-needs-segno", "2-coda jump without @segno (will play D.C., not D.S.)");
  }

  return findings;
}

/** Python tok.strip("()"). */
function stripParens(s: string): string {
  return s.replace(/^[()]+/, "").replace(/[()]+$/, "");
}

/** Format a tuple-ish list for the (non-normative) message; matches Python's repr loosely. */
function fmt(pattern: number[]): string {
  return `(${pattern.join(", ")})`;
}
