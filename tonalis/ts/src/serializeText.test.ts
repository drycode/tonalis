/**
 * Tests for the canonical DSL text printer (Phase 2 §1.1). Two gates: (1) IR -> text -> IR
 * identity over crafted cases; (2) IR -> text golden strings (a shared parser/printer bug passes
 * identity alone, so the golden is mandatory). Mirrors the Python `test_serialize_text.py`.
 */

import { describe, it, expect } from "vitest";
import type { LeadSheet } from "./ast.js";
import { parseDsl } from "./parser.js";
import { serialize } from "./serializeText.js";

/**
 * Zero out the `line` source-position artifact so identity compares lead-sheet semantics. `line`
 * is a source-line index, not part of the chart's identity; the canonical printer re-flows the
 * layout (blank line before each section, one body line per section), so absolute line numbers
 * shift while every semantic field (cells/kind/barline/nav/hints) is preserved. Mirrors the Python
 * ref's `_norm`.
 */
function norm(chart: LeadSheet): LeadSheet {
  for (const s of chart.sections) for (const m of s.measures) m.line = 0;
  return chart;
}

describe("canonical DSL text printer", () => {
  const cases = [
    "title: T\nkey: C\ntime: 4/4\n[A]\n| C6 | A-7 |\n",
    "title: T\nkey: C\ntime: 4/4\n[Intro]\n| D-7 | G7 |\n@break\n[A]\n| C6 | A-7 |\n",
    "title: T\nkey: C\ntime: 4/4\n[A]\n@fine\n| C6 |\n",
    "title: T\nkey: C\ntime: 4/4\n[A]\n{ | C^7 |1. A-7 } |2. F6 ||\n",
  ];
  for (const dsl of cases) {
    it(`round-trips identity: ${dsl.slice(20, 40)}`, () => {
      const ir = parseDsl(dsl).chart;
      expect(ir).not.toBeNull();
      const text = serialize(ir!);
      const ir2 = parseDsl(text).chart;
      expect(ir2).not.toBeNull();
      expect(norm(ir2!)).toEqual(norm(ir!));
    });
  }

  it("emits @break for a break hint and round-trips", () => {
    const dsl =
      "title: T\nkey: C\ntime: 4/4\n[Intro]\n| D-7 | G7 |\n@break\n[A]\n| C6 | A-7 |\n";
    const ir = parseDsl(dsl).chart!;
    const text = serialize(ir);
    expect(text).toContain("@break");
    expect(norm(parseDsl(text).chart!)).toEqual(norm(ir));
  });

  it("emits @fine for a fine nav and round-trips", () => {
    const dsl = "title: T\nkey: C\ntime: 4/4\n[A]\n@fine\n| C6 |\n";
    const ir = parseDsl(dsl).chart!;
    const text = serialize(ir);
    expect(text).toContain("@fine");
    expect(norm(parseDsl(text).chart!)).toEqual(norm(ir));
  });

  it("golden: simple", () => {
    const ir = parseDsl("title: T\nkey: C\ntime: 4/4\n[A]\n| C6 | A-7 |\n").chart!;
    expect(serialize(ir)).toBe("title: T\nkey: C\ntime: 4/4\n\n[A]\n| C6 | A-7 |\n");
  });

  it("golden: repeat/ending/final round-trips with canonical glyphs", () => {
    const ir = parseDsl("title: T\nkey: C\ntime: 4/4\n[A]\n{ | C^7 |1. A-7 } |2. F6 ||\n").chart!;
    const out = serialize(ir);
    expect(norm(parseDsl(out).chart!)).toEqual(norm(ir));
    expect(out).toContain("{ ");
    expect(out).toContain("}");
    expect(out).toContain("||");
    expect(out).toContain("1.");
    expect(out).toContain("2.");
  });
});
