/**
 * transactions.test.ts — TDD unit tests for modulate / isDiatonic / harmonicFunctionInKey / chordInKey.
 * Written BEFORE implementation (Step 1: failing tests).
 */
import { describe, it, expect } from "vitest";
import { modulate, isDiatonic, harmonicFunctionInKey, chordInKey } from "./transactions.js";
import { parseChord } from "./chord.js";

// ---------------------------------------------------------------------------
// modulate — Notes path
// ---------------------------------------------------------------------------

describe("modulate — Notes path", () => {
  it("C up P5(7) → G", () => {
    expect(modulate(7, "C")).toBe("G");
  });

  it("D up m3(3) → F", () => {
    expect(modulate(3, "D")).toBe("F");
  });

  it("Ab up M2(2) → Bb", () => {
    expect(modulate(2, "Ab")).toBe("Bb");
  });
});

// ---------------------------------------------------------------------------
// modulate — ScaleDegree path
// ---------------------------------------------------------------------------

describe("modulate — ScaleDegree path", () => {
  it("bVII up P5(7) → IV", () => {
    expect(modulate(7, "bVII")).toBe("IV");
  });

  it("ii (minor) up M2(2) → iii", () => {
    expect(modulate(2, "ii")).toBe("iii");
  });

  it("V up Tritone(6) → #I", () => {
    expect(modulate(6, "V")).toBe("#I");
  });
});

// ---------------------------------------------------------------------------
// isDiatonic — Major
// ---------------------------------------------------------------------------

describe("isDiatonic — Major", () => {
  it("C^7 diatonic to C major", () => {
    const chord = parseChord("C^7");
    expect(isDiatonic("C", "Major", chord)).toBe(true);
  });

  it("G7 diatonic to C major", () => {
    const chord = parseChord("G7");
    expect(isDiatonic("C", "Major", chord)).toBe(true);
  });

  it("Db^7 NOT diatonic to C major", () => {
    const chord = parseChord("Db^7");
    expect(isDiatonic("C", "Major", chord)).toBe(false);
  });

  it("D7 diatonic to G major", () => {
    const chord = parseChord("D7");
    expect(isDiatonic("G", "Major", chord)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// isDiatonic — Minor / HarmonicMinor
// ---------------------------------------------------------------------------

describe("isDiatonic — Minor + HarmonicMinor", () => {
  it("C-7 diatonic to C minor", () => {
    const chord = parseChord("C-7");
    expect(isDiatonic("C", "Minor", chord)).toBe(true);
  });

  it("Bb7 diatonic to C minor", () => {
    const chord = parseChord("Bb7");
    expect(isDiatonic("C", "Minor", chord)).toBe(true);
  });

  it("G7 diatonic to C HarmonicMinor", () => {
    const chord = parseChord("G7");
    expect(isDiatonic("C", "HarmonicMinor", chord)).toBe(true);
  });

  it("Bb^7 NOT diatonic to C HarmonicMinor", () => {
    const chord = parseChord("Bb^7");
    expect(isDiatonic("C", "HarmonicMinor", chord)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// harmonicFunctionInKey
// ---------------------------------------------------------------------------

describe("harmonicFunctionInKey", () => {
  it("C-7 in C minor → Tonic (minor tonic special case)", () => {
    const chord = parseChord("C-7");
    expect(harmonicFunctionInKey("C", true, chord)).toBe("Tonic");
  });

  it("C^7 in C major → Tonic", () => {
    const chord = parseChord("C^7");
    expect(harmonicFunctionInKey("C", false, chord)).toBe("Tonic");
  });

  it("G7 in C major → Dominant", () => {
    const chord = parseChord("G7");
    expect(harmonicFunctionInKey("C", false, chord)).toBe("Dominant");
  });

  it("C7 in C major (blues I7) → Dominant", () => {
    const chord = parseChord("C7");
    expect(harmonicFunctionInKey("C", false, chord)).toBe("Dominant");
  });

  it("D-7 in C major → Subdominant", () => {
    const chord = parseChord("D-7");
    expect(harmonicFunctionInKey("C", false, chord)).toBe("Subdominant");
  });
});

// ---------------------------------------------------------------------------
// chordInKey
// ---------------------------------------------------------------------------

describe("chordInKey", () => {
  it("V7 in C → G7", () => {
    const chord = chordInKey("V7", "C");
    expect(chord.root).toBe("G");
    expect(chord.seventh).toBe("7");
    expect(chord.harmonic_function).toBe("Dominant");
  });

  it("ii-7 in C → D-7", () => {
    const chord = chordInKey("ii-7", "C");
    expect(chord.root).toBe("D");
    expect(chord.triad).toBe("-");
    expect(chord.seventh).toBe("7");
  });

  it("I^7 in C → C^7", () => {
    const chord = chordInKey("I^7", "C");
    expect(chord.root).toBe("C");
    expect(chord.seventh).toBe("^7");
  });

  it("V7/V in C → D7 (slash chord: denom V→G, then V off G→D)", () => {
    const chord = chordInKey("V7/V", "C");
    expect(chord.root).toBe("D");
    expect(chord.seventh).toBe("7");
    expect(chord.harmonic_function).toBe("Dominant");
  });

  it("bVI^7 in C → Ab^7", () => {
    const chord = chordInKey("bVI^7", "C");
    expect(chord.root).toBe("Ab");
    expect(chord.seventh).toBe("^7");
  });

  it("V7 in G → D7", () => {
    const chord = chordInKey("V7", "G");
    expect(chord.root).toBe("D");
  });
});
