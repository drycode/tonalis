/**
 * from_json cross-impl rejection contract (TS). The canonical JSON is a public interface: the
 * Py/TS/Rust ports must reject the SAME malformed inputs the SAME way — throw a clean Error, never
 * silently coerce an unknown kind/barline or accept a string/null schema_version as v1. Mirrors the
 * Python `test_serialize.py` rejection tests + the Rust `unit.rs` `from_json_rejects_*` tests.
 */
import { describe, it, expect } from "vitest";
import { astFromJson, astToJson, type LeadSheetJson } from "./ast.js";

function baseJson(): LeadSheetJson {
  return {
    schema_version: 1,
    meta: { title: "T" },
    sections: [
      {
        label: "A",
        kind: "a",
        measures: [
          {
            cells: [{ chord: "C", beats: null, alt: null }],
            ending: null,
            bar_open: false,
            barline: "normal",
            nav: [],
            hints: [],
            line: 0,
          },
        ],
      },
    ],
  };
}

describe("astFromJson rejection contract", () => {
  it("round-trips a valid canonical object", () => {
    const j = baseJson();
    const back = astFromJson(j);
    expect(astToJson(back)).toEqual(j);
  });

  it("rejects an unknown Section.kind (e.g. 'bridge') — not coerced", () => {
    const j = baseJson();
    (j.sections[0] as { kind: string }).kind = "bridge";
    expect(() => astFromJson(j)).toThrow();
  });

  it("rejects an unknown Measure.barline (e.g. 'double') — not raw passthrough", () => {
    const j = baseJson();
    (j.sections[0]!.measures[0] as { barline: string }).barline = "double";
    expect(() => astFromJson(j)).toThrow();
  });

  it("rejects a string schema_version '2' (not accepted as v1)", () => {
    const j = baseJson() as { schema_version: unknown };
    j.schema_version = "2";
    expect(() => astFromJson(j as LeadSheetJson)).toThrow();
  });

  it("rejects a null schema_version (not accepted as v1)", () => {
    const j = baseJson() as { schema_version: unknown };
    j.schema_version = null;
    expect(() => astFromJson(j as LeadSheetJson)).toThrow();
  });

  it("rejects a string schema_version '1' (a string is not the integer 1)", () => {
    const j = baseJson() as { schema_version: unknown };
    j.schema_version = "1";
    expect(() => astFromJson(j as LeadSheetJson)).toThrow();
  });

  it("rejects a non-1 integer schema_version", () => {
    const j = baseJson();
    j.schema_version = 2;
    expect(() => astFromJson(j)).toThrow();
  });

  it("accepts a MISSING schema_version (defaults to 1)", () => {
    const j = baseJson() as Partial<LeadSheetJson>;
    delete j.schema_version;
    expect(() => astFromJson(j as LeadSheetJson)).not.toThrow();
  });
});
