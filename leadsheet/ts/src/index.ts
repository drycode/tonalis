/**
 * Public surface of the pure lead-sheet / chord-chart language core (parse · lint · chord-grammar
 * · AST · AST→JSON). iReal-agnostic: produces NO SCRUBBED:// URL — that is the ireal-codec package's
 * job. Depends only on the pure, zero-dependency music_dsl; browser + Node safe.
 *
 * Pure surface (SPEC.md §0): `parseDsl`, `lint`, `isValidChord`, `astToJson` + the AST types.
 */

export { parseDsl } from "./parser.js";
export { lint } from "./lint.js";
export { isValidChord } from "./chords.js";
export { astToJson, astFromJson, SCHEMA_VERSION } from "./ast.js";
export { serialize } from "./serializeText.js";
export type {
  Barline,
  Cell,
  CellJson,
  LeadSheet,
  LeadSheetJson,
  LintFinding,
  Measure,
  MeasureJson,
  Meta,
  MetaJson,
  NavItem,
  ParseResult,
  Section,
  SectionJson,
  SectionKind,
  Severity,
  Time,
} from "./ast.js";
