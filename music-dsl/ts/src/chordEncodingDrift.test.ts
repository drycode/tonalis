/**
 * Drift guard for the enum-derived value→name reverse maps behind
 * chordModelEncoding (DRY-430). transactions.ts used to carry a hardcoded
 * second copy of these maps, which silently diverged as enum members changed.
 * chord.ts is now the single source; this test walks EVERY Triad / Seventh /
 * Extensions member through the model-level encoder so that adding or renaming
 * a member without updating the reverse lookup fails loudly here rather than
 * mapping wrong downstream.
 */
import { describe, expect, it } from "vitest";
import { parseChord, chordModelEncoding, type ChordModel } from "./chord.js";
import { Triad, Seventh, Extensions } from "./chordQuality.js";

const BASE: ChordModel = parseChord("C");

describe("chordModelEncoding covers every quality-enum member", () => {
  it("encodes every Triad member", () => {
    for (const [name, value] of Object.entries(Triad)) {
      const model: ChordModel = { ...BASE, triad: value, seventh: Seventh._None, extensions: [] };
      expect(() => chordModelEncoding(model), `Triad.${name}`).not.toThrow();
    }
  });

  it("encodes every Seventh member", () => {
    for (const [name, value] of Object.entries(Seventh)) {
      const model: ChordModel = { ...BASE, seventh: value, extensions: [] };
      expect(() => chordModelEncoding(model), `Seventh.${name}`).not.toThrow();
    }
  });

  it("encodes every Extensions member", () => {
    for (const [name, value] of Object.entries(Extensions)) {
      const model: ChordModel = { ...BASE, extensions: [value] };
      expect(() => chordModelEncoding(model), `Extensions.${name}`).not.toThrow();
    }
  });

  it("string-level and model-level encoders agree", () => {
    for (const raw of ["C", "C7", "C-7", "Ch7", "C^7#11", "C7b9#5", "C-69"]) {
      expect(chordModelEncoding(parseChord(raw)), raw).toBe(
        chordModelEncoding({ ...parseChord(raw) }),
      );
    }
  });
});
