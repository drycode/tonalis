import { describe, it, expect } from "vitest";
import { isValidChord } from "./chords.js";

describe("isValidChord — non-chord wrapper + music_dsl delegation", () => {
  it("accepts no-chord markers, slash-bass, star-artifact, and real chords", () => {
    for (const t of ["N.C.", "n", "/A", "Bb*7+*", "C-7", "F^7", "G7b9", "C4", "C7+"]) {
      expect(isValidChord(t), t).toBe(true);
    }
  });
  it("rejects empty and malformed tokens (incl. the blessed C7777)", () => {
    for (const t of ["", "C7777", "H9", "xyz", "9"]) {
      expect(isValidChord(t), t).toBe(false);
    }
  });
});
