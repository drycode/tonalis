/**
 * chord.test.ts — TDD unit tests for parseChord / serializeChord / chordEncoding.
 * Written BEFORE implementation (Step 1: failing tests).
 */
import { describe, it, expect } from "vitest";
import { parseChord, serializeChord, chordEncoding, InvalidChordStringError } from "./chord.js";

describe("parseChord + serializeChord", () => {
  it("C^7#11 — major-7 with sharp-11 extension", () => {
    const chord = parseChord("C^7#11");
    const model = serializeChord(chord);
    expect(model).toEqual({
      root: "C",
      triad: "",
      seventh: "^7",
      extensions: ["#11"],
      harmonic_function: "Tonic",
      substitution: false,
    });
  });

  it("C#-7 — sharp root normalized to Db", () => {
    const chord = parseChord("C#-7");
    const model = serializeChord(chord);
    expect(model.root).toBe("Db");
    expect(model.triad).toBe("-");
    expect(model.seventh).toBe("7");
  });

  it("Csus — triad is 'sus' (not sus4)", () => {
    const chord = parseChord("Csus");
    const model = serializeChord(chord);
    expect(model.triad).toBe("sus");
    expect(model.seventh).toBe("");
    expect(model.extensions).toEqual([]);
  });

  it("C4 — sus4 shorthand, triad is 'sus4'", () => {
    const chord = parseChord("C4");
    const model = serializeChord(chord);
    expect(model.triad).toBe("sus4");
    expect(model.seventh).toBe("");
  });

  it("C7+ — aug5 folds into extensions as '#5'", () => {
    const chord = parseChord("C7+");
    const model = serializeChord(chord);
    expect(model.extensions).toContain("#5");
    expect(model.seventh).toBe("7");
  });

  it("C^7/E — slash discarded, same shape as C^7", () => {
    const withSlash = serializeChord(parseChord("C^7/E"));
    const withoutSlash = serializeChord(parseChord("C^7"));
    expect(withSlash).toEqual(withoutSlash);
  });

  it("bad input 'xyzzy' throws InvalidChordStringError", () => {
    expect(() => parseChord("xyzzy")).toThrow(InvalidChordStringError);
  });

  it("'C|D' (pipe) throws InvalidChordStringError", () => {
    expect(() => parseChord("C|D")).toThrow(InvalidChordStringError);
  });

  it("'B#b9' make_chord_attrs rejection throws InvalidChordStringError", () => {
    expect(() => parseChord("B#b9")).toThrow(InvalidChordStringError);
  });

  it("enharmonic root: Cb → B", () => {
    const model = serializeChord(parseChord("Cb"));
    expect(model.root).toBe("B");
  });

  it("enharmonic root: E# → F", () => {
    const model = serializeChord(parseChord("E#"));
    expect(model.root).toBe("F");
  });

  it("enharmonic root: Fb → E", () => {
    const model = serializeChord(parseChord("Fb"));
    expect(model.root).toBe("E");
  });

  it("enharmonic root: B# → C", () => {
    const model = serializeChord(parseChord("B#"));
    expect(model.root).toBe("C");
  });

  it("C^ (caret shorthand) → seventh is '^7'", () => {
    const model = serializeChord(parseChord("C^"));
    expect(model.seventh).toBe("^7");
  });

  it("Cadd9 → extensions ['9'] (add stripped)", () => {
    const model = serializeChord(parseChord("Cadd9"));
    expect(model.extensions).toEqual(["9"]);
  });

  it("C69 → extensions ['6', '9'] (69 normalization)", () => {
    const model = serializeChord(parseChord("C69"));
    expect(model.extensions).toEqual(["6", "9"]);
  });

  it("C7alt — alt extension, seventh forced to '7'", () => {
    const model = serializeChord(parseChord("C7alt"));
    expect(model.seventh).toBe("7");
    expect(model.extensions).toEqual(["alt"]);
    expect(model.harmonic_function).toBe("Dominant");
  });

  it("harmonic function table: C-7 → Subdominant", () => {
    const model = serializeChord(parseChord("C-7"));
    expect(model.harmonic_function).toBe("Subdominant");
  });

  it("harmonic function table: G7 → Dominant", () => {
    const model = serializeChord(parseChord("G7"));
    expect(model.harmonic_function).toBe("Dominant");
  });

  it("harmonic function table: C^7 → Tonic", () => {
    const model = serializeChord(parseChord("C^7"));
    expect(model.harmonic_function).toBe("Tonic");
  });

  it("substitution is always false for absolute Chord", () => {
    const model = serializeChord(parseChord("C-7"));
    expect(model.substitution).toBe(false);
  });
});

describe("chordEncoding", () => {
  it("C → 280576 (major triad encoding)", () => {
    expect(chordEncoding("C")).toBe(280576n);
  });

  it("C-7 → 297216", () => {
    expect(chordEncoding("C-7")).toBe(297216n);
  });

  it("invalid input throws", () => {
    expect(() => chordEncoding("xyzzy")).toThrow();
  });
});
