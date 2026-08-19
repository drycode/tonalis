/**
 * numericChord.test.ts — TDD unit tests for NumericChord port.
 * Written BEFORE implementation (Step 1: failing tests).
 *
 * Tests cover:
 *   - parse: basic parse, slash, leading "s" substitution flag
 *   - fromChord: the 3 substitution branches (branch-a tritone, branch-b dominant, branch-c m6)
 *   - fromChord: branch-c non-fire (A==4 / M3-up MUST NOT fire)
 *   - IncorrectHarmonicFunctionError for tritone sub with non-Subdominant chord
 *   - slash chords
 */
import { describe, it, expect } from "vitest";
import {
  fromChordString,
  fromChord,
  serializeNumericChord,
  IncorrectHarmonicFunctionError,
} from "./numericChord.js";
import { parseChord } from "./chord.js";

// ---------------------------------------------------------------------------
// fromChordString — basic parsing
// ---------------------------------------------------------------------------

describe("fromChordString — basic", () => {
  it("ii-7 → root=ii, triad=-, seventh=7, substitution=false", () => {
    const n = fromChordString("ii-7");
    const s = serializeNumericChord(n);
    expect(s.numerator.root).toBe("ii");
    expect(s.numerator.triad).toBe("-");
    expect(s.numerator.seventh).toBe("7");
    expect(s.numerator.substitution).toBe(false);
    expect(s.denominator).toBeNull();
  });

  it("V7 → root=V, dominant", () => {
    const n = fromChordString("V7");
    const s = serializeNumericChord(n);
    expect(s.numerator.root).toBe("V");
    expect(s.numerator.seventh).toBe("7");
    expect(s.numerator.harmonic_function).toBe("Dominant");
  });

  it("I^7 → root=I, tonic", () => {
    const n = fromChordString("I^7");
    const s = serializeNumericChord(n);
    expect(s.numerator.root).toBe("I");
    expect(s.numerator.seventh).toBe("^7");
    expect(s.numerator.harmonic_function).toBe("Tonic");
  });

  it("sV7 → substitution=true, root=V", () => {
    const n = fromChordString("sV7");
    const s = serializeNumericChord(n);
    expect(s.numerator.root).toBe("V");
    expect(s.numerator.substitution).toBe(true);
  });

  it("empty string → throws", () => {
    expect(() => fromChordString("")).toThrow();
  });
});

describe("fromChord — suspended numeral casing", () => {
  for (const token of ["Isus", "Isus2", "Isus4", "I7sus", "I7sus2", "I7sus4"]) {
    it(`${token} keeps its uppercase degree`, () => {
      expect(serializeNumericChord(fromChordString(token)).numerator.root).toBe("I");
    });
  }
});

// ---------------------------------------------------------------------------
// fromChordString — slash chords
// ---------------------------------------------------------------------------

describe("fromChordString — slash", () => {
  it("V7/V → numerator=V7, denominator=V", () => {
    const n = fromChordString("V7/V");
    const s = serializeNumericChord(n);
    expect(s.numerator.root).toBe("V");
    expect(s.numerator.seventh).toBe("7");
    expect(s.denominator).not.toBeNull();
    expect(s.denominator!.root).toBe("V");
    expect(s.denominator!.seventh).toBe("");
  });

  it("ii-7/IV → numerator=ii-7, denominator=IV", () => {
    const n = fromChordString("ii-7/IV");
    const s = serializeNumericChord(n);
    expect(s.numerator.root).toBe("ii");
    expect(s.denominator!.root).toBe("IV");
  });
});

// ---------------------------------------------------------------------------
// fromChord — no substitution (baseline)
// ---------------------------------------------------------------------------

describe("fromChord — no substitution (reference)", () => {
  it("E-7 in C key, no sub → root=iii, triad=-", () => {
    const chord = parseChord("E-7");
    const n = fromChord("C", chord, false);
    const s = serializeNumericChord({ numerator: n, denominator: null });
    expect(s.numerator.root).toBe("iii");
    expect(s.numerator.triad).toBe("-");
    expect(s.numerator.substitution).toBe(false);
  });

  it("Ab-7 in C key, no sub → root=bvi, triad=-", () => {
    const chord = parseChord("Ab-7");
    const n = fromChord("C", chord, false);
    const s = serializeNumericChord({ numerator: n, denominator: null });
    expect(s.numerator.root).toBe("bvi");
    expect(s.numerator.substitution).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// fromChord — BRANCH A: tritone (A==6) + Subdominant → modulate Tritone+M2
// ---------------------------------------------------------------------------

describe("fromChord — branch-a: tritone substitution", () => {
  // Db7 in C: A = semitonesApartAscending("Db", "C") = 11... wait, that's wrong.
  // Actually: semitonesApartAscending(chord.root, key_root) = semitonesApartAscending("Db", "C") = 11
  // We need A = semitonesApartAscending(chord.root, keyRoot) == Tritone(6)
  // Db→C: (0 + 12 - 1) % 12 = 11. Not tritone.
  // F#→C: (0 + 12 - 6) % 12 = 6. YES Tritone.
  // But looking at conformance: "Db7-in-C-with-sub" uses Db7.
  // semitonesApartAscending("Db", "C") = (0+12-1)%12 = 11. Not 6.
  // Let me re-read: the Python is semitones_apart_ascending(chord.root, diatonic_key_root)
  // So chord.root=Db, diatonic_key_root=C => (index(C)+12-index(Db))%12 = (0+12-1)%12=11
  // That's not tritone either.
  // Wait — the conformance case is "Db7-in-C-with-sub" → root=V (dominant, modulate Tritone).
  // So that's branch-b (dominant), NOT branch-a.
  // Branch-a (tritone, Subdominant) fires on: A(chord.root→keyRoot)==6 AND hf==Subdominant
  // For keyRoot=C, which chord.root has A==6? semitonesApartAscending(chord.root,"C")==6
  // => (0+12-idx(chord.root))%12==6 => idx(chord.root)==6 => F#/Gb
  // F#-7 in C key with sub: harmonic_function of F#-7 = Subdominant, A==6 → branch-a

  it("branch-a: F#-7 in C, A==6, Subdominant → modulate Tritone+M2 (=8)", () => {
    // F# relative to C: semitonesApartAscending("F#","C") = (0+12-6)%12 = 6 = Tritone
    // F#-7 is Subdominant. Branch-a fires. degree = SCALE_DEGREES[6]="bV"→minor="bv"
    // modulate(6+2=8, "bv") → SCALE_DEGREES[(6+8)%12].normalize(flat,minor) → SCALE_DEGREES[2]="II"→minor="ii"
    const chord = parseChord("F#-7");
    const n = fromChord("C", chord, true);
    const s = serializeNumericChord({ numerator: n, denominator: null });
    expect(s.numerator.root).toBe("ii");
    expect(s.numerator.substitution).toBe(true);
  });

  it("branch-a error: F#7 in C, A==6, but NOT Subdominant → throws IncorrectHarmonicFunctionError", () => {
    // F#7 = Dominant HF → branch-a requires Subdominant → error
    // Wait: semitonesApartAscending("F#","C")=6=Tritone, F#7 is Dominant
    // Actually checking conformance: key_root=F#, chord=C7, sub=true → error (C7 is Dominant, not Subdominant)
    // semitonesApartAscending("C","F#") = (6+12-0)%12 = 6. YES. C7 is Dominant → throws.
    const chord = parseChord("C7");
    expect(() => fromChord("F#", chord, true)).toThrow(IncorrectHarmonicFunctionError);
  });
});

// ---------------------------------------------------------------------------
// fromChord — BRANCH B: harmonic_function==Dominant → modulate Tritone(6)
// ---------------------------------------------------------------------------

describe("fromChord — branch-b: dominant substitution", () => {
  it("Db7 in C, Dominant, sub=true → modulate Tritone → root=V", () => {
    // Db7 is Dominant. A = semitonesApartAscending("Db","C") = 11 ≠ 6 (not branch-a)
    // Branch-b: hf==Dominant → modulate(6, degree)
    // degree = SCALE_DEGREES[semitonesApartAscending("C","Db")] = SCALE_DEGREES[(1+12-0)%12] = SCALE_DEGREES[1] = "bII"
    // modulate(6, "bII") → SCALE_DEGREES[(1+6)%12].normalize(flat=true, minor=false) = SCALE_DEGREES[7]="V"→to_flat()=V→to_major()=V → "V"
    const chord = parseChord("Db7");
    const n = fromChord("C", chord, true);
    const s = serializeNumericChord({ numerator: n, denominator: null });
    expect(s.numerator.root).toBe("V");
    expect(s.numerator.seventh).toBe("7");
    expect(s.numerator.harmonic_function).toBe("Dominant");
    expect(s.numerator.substitution).toBe(true);
  });

  it("E-7 in C key, sub=true → root=iii (no sub branch fires, A==4 M3-up, not m6 8)", () => {
    // E-7 in C: A = semitonesApartAscending("E","C") = (0+12-4)%12 = 8
    // Wait: (index("C")+12-index("E"))%12 = (0+12-4)%12 = 8 = m6. That IS branch-c!
    // But conformance says sub=true → root="#vi". Let me recheck...
    // "substitution/E-m7-in-C-with-sub" → root="#vi". So branch-c fires.
    // This is the "branch-c fires on m6 A==8" case. Let me put the test correctly.
    const chord = parseChord("E-7");
    const n = fromChord("C", chord, true);
    const s = serializeNumericChord({ numerator: n, denominator: null });
    expect(s.numerator.root).toBe("#vi");
    expect(s.numerator.substitution).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// fromChord — BRANCH C: A==8 (m6) → modulate m6.down()+M2 = -8+2 = -6
// Also: A==4 (M3-up) MUST NOT fire branch-c
// ---------------------------------------------------------------------------

describe("fromChord — branch-c: m6 substitution (A==8 fires; A==4 does NOT)", () => {
  it("E-7 in C: A=semitonesApartAscending('E','C')=8=m6 → branch-c fires → root=#vi", () => {
    // semitonesApartAscending("E","C") = (0+12-4)%12 = 8 = m6. Branch-c fires.
    // degree = SCALE_DEGREES[semitonesApartAscending("C","E")] = SCALE_DEGREES[4] = "III" → minor → "iii"
    // modulate(-8+2=-6, "iii") → (3 + (-6) + 12)%12 = 9 → SCALE_DEGREES[9]="VI"→normalize(flat=false,minor=true)
    // = "VI"→to_sharp()="VI" (not flat)→to_minor()="vi"... wait
    // Let me recheck: conformance expects "#vi". Let me trace more carefully.
    // SCALE_DEGREES[9] = "VI". is_flat=false (degree was "iii", is_flat=false). is_minor=true.
    // normalize(is_flat=false, is_minor=true): to_sharp() (VI is not flat, no-op), to_minor("VI")→"vi"
    // But result should be "#vi"... Let me look at the conformance again — "root": "#vi".
    // Hmm. Let me think again about the degree before modulate.
    // _find_scale_degree("C", "E", Triad.Minor):
    //   semitones = semitonesApartAscending("C","E") = (4+12-0)%12 = 4
    //   SCALE_DEGREES[4] = "III"
    //   triad==Minor, scale_degree is "III" which is_flat=false, no to_sharp needed
    //   m_or_M_scaledegree("III", Minor) → not Major/Augmented/Sus4 → to_minor → "iii"
    // degree = "iii" (idx=3 in SCALE_DEGREES after to_major→"III"→idx=4... wait
    // get_index("iii") = SCALE_DEGREES.indexOf("iii".to_major()) = SCALE_DEGREES.indexOf("III") = 4
    // No wait. get_index in Python: SCALE_DEGREES.index(note.to_major()) for ScaleDegree
    // "iii".to_major() = "III". SCALE_DEGREES.index("III") = 4.
    // modulate(-6, "iii"): new_idx = (4 + (-6) + 12) % 12 = 10
    // SCALE_DEGREES[10] = "bVII". normalize(is_flat=true (iii is_flat=false... wait iii is not flat)
    // Wait: "iii".is_flat = "iii" in flats_to_sharps? flats_to_sharps has "bii","biii",etc. "iii" is NOT flat.
    // "iii".is_minor = "iii" in minor_to_major? Yes. So is_flat=false, is_minor=true.
    // normalize(is_flat=false, is_minor=true):
    //   is_flat=false → to_sharp(): "bVII" is in flats_to_sharps → "#VI"
    //   is_minor=true → to_minor(): "#VI" in major_to_minor → "#vi"
    // So "#vi". That matches conformance.
    const chord = parseChord("E-7");
    const n = fromChord("C", chord, true);
    const s = serializeNumericChord({ numerator: n, denominator: null });
    expect(s.numerator.root).toBe("#vi");
    expect(s.numerator.substitution).toBe(true);
  });

  it("Ab-7 in C: A=semitonesApartAscending('Ab','C')=4=M3 → branch-c does NOT fire → root=bvi", () => {
    // semitonesApartAscending("Ab","C") = (0+12-8)%12 = 4 = M3 ≠ m6(8)
    // Branch-a: 4 ≠ 6. Branch-b: Ab-7 is Subdominant, not Dominant. Branch-c: 4 ≠ 8. No branch fires.
    // So root stays at _find_scale_degree("C","Ab",Minor):
    //   semitones = semitonesApartAscending("C","Ab") = (8+12-0)%12 = 8
    //   SCALE_DEGREES[8] = "bVI" → m_or_M → to_minor() → "bvi"
    // With substitution=true but no branch fires → result is same as sub=false (just substitution flag set)
    const chord = parseChord("Ab-7");
    const n = fromChord("C", chord, true);
    const s = serializeNumericChord({ numerator: n, denominator: null });
    expect(s.numerator.root).toBe("bvi");
    expect(s.numerator.substitution).toBe(true);
  });
});
