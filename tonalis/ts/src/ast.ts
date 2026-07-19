/**
 * DSL abstract syntax (Phase 2 — NEUTRAL IR) + the canonical JSON projection (SPEC.md §2.1).
 * The root is `LeadSheet`; sections carry a neutral `kind`; measures carry a `barline` enum and an
 * opaque `hints` list (where `@break` lives). No format-specific value is stored — a downstream codec maps these.
 * Mirrors the Python reference `tonalis/ast.py` + `tonalis/serialize.py`.
 */

/** A meter as a [numerator, denominator] pair. */
export type Time = [number, number];

/** Neutral section role, derived by the parser from the bracket name. */
export type SectionKind = "a" | "b" | "c" | "d" | "intro" | "verse";

/** Neutral right-barline. '|' -> normal, '}' -> repeat_end, 'Z'/'||' -> final. */
export type Barline = "normal" | "repeat_end" | "final";

/** A navigation item attached to a measure (SPEC.md §2.1). Tuple-shaped, like the Python ref. */
export type NavItem =
  | ["segno"]
  | ["coda"]
  | ["tocoda"]
  | ["fine"]
  | ["text", string]
  | ["time", Time];

export interface Cell {
  chord: string;
  /** explicit `:N`, else null (even split of the bar) */
  beats: number | null;
  /** raw "(A-7 D7)" alt-chord text including parens, or null */
  alt: string | null;
}

export interface Measure {
  cells: Cell[];
  /** 1./2. nth-ending number, or null */
  ending: number | null;
  /** preceded by '{' */
  bar_open: boolean;
  /** neutral right-barline (was bar_close glyph) */
  barline: Barline;
  /** semantic navigation items, in render order */
  nav: NavItem[];
  /** opaque render-hints, e.g. "break"; NO lead-sheet semantics */
  hints: string[];
  /** source line for findings */
  line: number;
}

export interface Section {
  label: string;
  /** neutral role (the parser derives it from the bracket name) */
  kind: SectionKind;
  measures: Measure[];
}

export interface Meta {
  title?: string;
  composer?: string;
  style?: string;
  key?: string;
  time?: Time;
}

export interface LeadSheet {
  meta: Meta;
  sections: Section[];
}

export type Severity = "error" | "warning";

export interface LintFinding {
  severity: Severity;
  line: number;
  code: string;
  message: string;
}

export interface ParseResult {
  chart: LeadSheet | null;
  findings: LintFinding[];
}

// --- canonical JSON projection (SPEC.md §2.1) ---------------------------------------------

export const SCHEMA_VERSION = 1;

/** Stable JSON shape for one cell. Key order is fixed: chord, beats, alt. */
export interface CellJson {
  chord: string;
  beats: number | null;
  alt: string | null;
}

/** Stable JSON shape for one measure. Key order fixed per §2.1. */
export interface MeasureJson {
  cells: CellJson[];
  ending: number | null;
  bar_open: boolean;
  barline: Barline;
  nav: unknown[];
  hints: string[];
  line: number;
}

export interface SectionJson {
  label: string;
  kind: SectionKind;
  measures: MeasureJson[];
}

export interface MetaJson {
  [k: string]: string | [number, number];
}

export interface LeadSheetJson {
  schema_version: number;
  meta: MetaJson;
  sections: SectionJson[];
}

const META_ORDER: Array<keyof Meta> = ["title", "composer", "style", "key", "time"];

function metaToJson(meta: Meta): MetaJson {
  // Preserve insertion order of how the parser populated meta, mirroring the Python dict.
  // The parser inserts in header-encounter order; we replay that by iterating own keys.
  const out: MetaJson = {};
  for (const k of Object.keys(meta) as Array<keyof Meta>) {
    const v = meta[k];
    if (v === undefined) continue;
    if (k === "time" && Array.isArray(v)) {
      out[k] = [v[0], v[1]];
    } else {
      out[k] = v as string;
    }
  }
  return out;
}

function navToJson(nav: NavItem[]): unknown[] {
  return nav.map((item) => item.map((atom) => (Array.isArray(atom) ? [...atom] : atom)));
}

function cellToJson(c: Cell): CellJson {
  return { chord: c.chord, beats: c.beats, alt: c.alt };
}

function measureToJson(m: Measure): MeasureJson {
  return {
    cells: m.cells.map(cellToJson),
    ending: m.ending,
    bar_open: m.bar_open,
    barline: m.barline,
    nav: navToJson(m.nav),
    hints: [...m.hints],
    line: m.line,
  };
}

function sectionToJson(s: Section): SectionJson {
  return { label: s.label, kind: s.kind, measures: s.measures.map(measureToJson) };
}

/** Serialize a LeadSheet to the canonical JSON-able object (SPEC.md §2.1). */
export function astToJson(chart: LeadSheet): LeadSheetJson {
  return {
    schema_version: SCHEMA_VERSION,
    meta: metaToJson(chart.meta),
    sections: chart.sections.map(sectionToJson),
  };
}

/** Runtime allow-sets mirroring the SectionKind / Barline string-literal unions (so from_json can
 * REJECT an unknown value rather than pass it through untyped — the canonical JSON is a public
 * interface and malformed input is rejected uniformly across the Py/TS/Rust ports). */
const SECTION_KINDS = new Set<SectionKind>(["a", "b", "c", "d", "intro", "verse"]);
const BARLINES = new Set<Barline>(["normal", "repeat_end", "final"]);

/**
 * Inverse: rebuild a LeadSheet from canonical JSON. Rejects (throws an Error) an unknown major
 * `schema_version`, an unknown `Section.kind`, or an unknown `Measure.barline` — uniformly with
 * the Python/Rust ports. Missing `schema_version` defaults to 1; a non-1 integer, a string ("2"),
 * or `null` are all rejected cleanly (NOT silently coerced to v1).
 */
export function astFromJson(d: unknown): LeadSheet {
  // Input is untrusted (typed `unknown`, not `LeadSheetJson`): the canonical JSON
  // is a public interface, so we validate rather than assume the declared shape.
  const rawVer = (d as { schema_version?: unknown }).schema_version;
  // Missing -> default 1 (accept). Present must be exactly the integer SCHEMA_VERSION: a string,
  // null, boolean, or non-1 number all reject (do NOT let `null ?? 1` quietly accept null as v1).
  if (rawVer !== undefined) {
    if (typeof rawVer !== "number" || !Number.isInteger(rawVer) || rawVer !== SCHEMA_VERSION) {
      throw new Error(
        `unsupported schema_version ${JSON.stringify(rawVer)}; this build understands ${SCHEMA_VERSION}`,
      );
    }
  }
  const doc = d as LeadSheetJson;
  const meta: Meta = {};
  for (const [k, v] of Object.entries(doc.meta)) {
    if (k === "time" && Array.isArray(v)) meta.time = [v[0]!, v[1]!];
    else (meta as Record<string, unknown>)[k] = v;
  }
  const sections: Section[] = doc.sections.map((s) => {
    if (!SECTION_KINDS.has(s.kind)) {
      throw new Error(`unknown Section.kind ${JSON.stringify(s.kind)}`);
    }
    return {
      label: s.label,
      kind: s.kind,
      measures: s.measures.map((m) => {
        if (!BARLINES.has(m.barline)) {
          throw new Error(`unknown Measure.barline ${JSON.stringify(m.barline)}`);
        }
        return {
          cells: m.cells.map((c) => ({ chord: c.chord, beats: c.beats, alt: c.alt })),
          ending: m.ending,
          bar_open: m.bar_open,
          barline: m.barline,
          nav: m.nav as NavItem[],
          hints: [...m.hints],
          line: m.line,
        };
      }),
    };
  });
  return { meta, sections };
}

// Re-export the meta key order in case a caller wants a deterministic ordering helper.
export { META_ORDER };
