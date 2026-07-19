/**
 * Deterministic canonical-DSL printer: LeadSheet -> DSL text (Phase 2 §1.1). Mirrors the Python
 * reference `tonalis/serialize_text.py`; `parseDsl(serialize(ir)) == ir` is gated by the
 * conformance suite (and the unit goldens below). This is the only place IR -> text lives.
 */

import type { Barline, Cell, LeadSheet, Measure, Section } from "./ast.js";

const HEADER_ORDER: Array<keyof LeadSheet["meta"]> = [
  "title",
  "composer",
  "style",
  "key",
  "time",
];
const BARLINE_GLYPH: Record<Barline, string> = {
  normal: "|",
  repeat_end: "}",
  final: "||",
};

function header(meta: LeadSheet["meta"]): string {
  const out: string[] = [];
  for (const k of HEADER_ORDER) {
    const v = meta[k];
    if (v === undefined) continue;
    if (k === "time" && Array.isArray(v)) out.push(`time: ${v[0]}/${v[1]}`);
    else out.push(`${k}: ${v}`);
  }
  return out.join("\n");
}

function cellStr(c: Cell): string {
  let s = c.chord;
  if (c.beats !== null) s += `:${c.beats}`;
  if (c.alt) {
    // A single-token alt glues inline (`G7(Db7)`, the grammar's "inline alt, no space" form),
    // but a MULTI-token alt carries an interior space (`(A-7 D7)`) and the glued form
    // `G7(A-7 D7)` re-tokenizes wrong (the cell scanner `\([^)]*\)|\S+` breaks at the space).
    // Emit the separated `chord (alt)` form so `parse(serialize(ir)) == ir` holds (SPEC §2.1).
    s += (c.alt.includes(" ") ? " " : "") + c.alt;
  }
  return s;
}

function navBefore(m: Measure): string[] {
  const out: string[] = [];
  for (const item of m.nav) {
    const head = item[0];
    if (head === "segno") out.push("@segno");
    else if (head === "coda") out.push("@coda");
    else if (head === "fine") out.push("@fine");
    else if (head === "text") out.push(item[1] as string);
    else if (head === "time") {
      const t = item[1] as [number, number];
      out.push(`[time: ${t[0]}/${t[1]}]`);
    }
    // tocoda is emitted AFTER the measure (see navAfter)
  }
  return out;
}

function navAfter(m: Measure): string[] {
  return m.nav.filter((i) => i[0] === "tocoda").map(() => "@tocoda");
}

function measureStr(m: Measure, firstOnLine: boolean): string {
  // Canonical body line: a leading "| " opens the line, measures are "| "-joined, and each
  // measure ends with its barline glyph. A repeat-open prefixes "{ ".
  const prefix = m.bar_open ? "{ " : firstOnLine ? "| " : "";
  let body = "";
  if (m.ending !== null) body += `${m.ending}. `;
  body += m.cells.map(cellStr).join(" ");
  return `${prefix}${body} ${BARLINE_GLYPH[m.barline]}`;
}

function sectionText(s: Section): string {
  // One body line per section (parser-faithful): directives (@break/@segno/.../<text>) sit on
  // their own line and FLUSH the in-progress measure line before them; @tocoda flushes after.
  const lines = [`[${s.label}]`];
  let run: string[] = []; // measures accumulating on the current body line

  const flush = (): void => {
    if (run.length > 0) {
      lines.push(run.join(" "));
      run = [];
    }
  };

  for (const m of s.measures) {
    const before: string[] = [];
    for (const h of m.hints) if (h === "break") before.push("@break");
    before.push(...navBefore(m));
    if (before.length > 0) {
      flush();
      lines.push(...before);
    }
    run.push(measureStr(m, run.length === 0));
    const after = navAfter(m);
    if (after.length > 0) {
      flush();
      lines.push(...after);
    }
  }
  flush();
  return lines.join("\n");
}

/** Canonical DSL text for a LeadSheet (trailing newline; blank line before each section). */
export function serialize(chart: LeadSheet): string {
  const parts = [header(chart.meta)];
  for (const s of chart.sections) {
    parts.push(""); // blank line before each section
    parts.push(sectionText(s));
  }
  return parts.join("\n") + "\n";
}
