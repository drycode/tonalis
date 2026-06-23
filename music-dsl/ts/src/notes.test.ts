import { describe, it, expect } from "vitest";
import { notesEqual, noteIndex, noteToFlat, noteValue } from "./index";

describe("Notes", () => {
  it("enharmonic equality (C# == Db), distinct otherwise", () => {
    expect(notesEqual("C#", "Db")).toBe(true);
    expect(notesEqual("A#", "Bb")).toBe(true);
    expect(notesEqual("C", "D")).toBe(false);
  });
  it("chromatic index 0-11 via TWELVE_TONES", () => {
    expect(noteIndex("C")).toBe(0);
    expect(noteIndex("C#")).toBe(1);
    expect(noteIndex("Db")).toBe(1);
    expect(noteIndex("B")).toBe(11);
  });
  it("to_flat normalizes sharps to flats (root-spelling canonicalization, m6)", () => {
    expect(noteValue(noteToFlat("C#"))).toBe("Db");
    expect(noteValue(noteToFlat("D"))).toBe("D");
  });
});
