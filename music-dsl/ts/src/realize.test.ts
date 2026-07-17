/**
 * realize.test.ts — Unit tests for realize.ts and measure.ts (TDD: write first, impl passes).
 */
import { describe, it, expect } from "vitest";
import { noteToMidi, midiToHz, intervalPitches, chordPitches, scalePitches, scaleDegreePitch } from "./realize.js";
import { parseMeasure } from "./measure.js";
import { InvalidChordStringError } from "./chord.js";

describe("noteToMidi", () => {
  it("C4 = 60", () => expect(noteToMidi("C", 4)).toBe(60));
  it("A4 = 69", () => expect(noteToMidi("A", 4)).toBe(69));
  it("C5 = 72", () => expect(noteToMidi("C", 5)).toBe(72));
  it("G4 = 67", () => expect(noteToMidi("G", 4)).toBe(67));
  it("Db4 = 61", () => expect(noteToMidi("Db", 4)).toBe(61));
});

describe("midiToHz", () => {
  it("69 = 440.0", () => expect(midiToHz(69)).toBe(440.0));
  it("60 = 261.6256", () => expect(midiToHz(60)).toBe(261.6256));
});

describe("intervalPitches", () => {
  it("C4 P5 = [60, 67]", () => expect(intervalPitches("C", "P5", 4)).toEqual([60, 67]));
  it("A4 Octave = [69, 81]", () => expect(intervalPitches("A", "Octave", 4)).toEqual([69, 81]));
});

describe("chordPitches", () => {
  it("C^7 = [60,64,67,71]", () => expect(chordPitches("C^7", 4)).toEqual([60, 64, 67, 71]));
  it("C-7 = [60,63,67,70]", () => expect(chordPitches("C-7", 4)).toEqual([60, 63, 67, 70]));
  it("C7 = [60,64,67,70]", () => expect(chordPitches("C7", 4)).toEqual([60, 64, 67, 70]));
  it("Co7 dim7 rule = [60,63,66,69]", () => expect(chordPitches("Co7", 4)).toEqual([60, 63, 66, 69]));
  it("Ch7 half-dim = [60,63,66,70]", () => expect(chordPitches("Ch7", 4)).toEqual([60, 63, 66, 70]));
  it("C7b9 b9-as-12 = [60,64,67,70,72]", () => expect(chordPitches("C7b9", 4)).toEqual([60, 64, 67, 70, 72]));
  it("C13 no-b7 = [60,64,67,78]", () => expect(chordPitches("C13", 4)).toEqual([60, 64, 67, 78]));
  it("C+ augmented = [60,64,68]", () => expect(chordPitches("C+", 4)).toEqual([60, 64, 68]));
  it("Csus4 = [60,65,67]", () => expect(chordPitches("Csus4", 4)).toEqual([60, 65, 67]));
});

describe("scalePitches BigInt", () => {
  it("C Major octave 4 = 8 pitches incl. octave", () => {
    expect(scalePitches("C", "Major", 4)).toEqual([60, 62, 64, 65, 67, 69, 71, 72]);
  });
  it("C Minor octave 4", () => {
    expect(scalePitches("C", "Minor", 4)).toEqual([60, 62, 63, 65, 67, 68, 70, 72]);
  });
  it("unknown scale throws", () => {
    expect(() => scalePitches("C", "NotAScale", 4)).toThrow();
  });
});

describe("scaleDegreePitch", () => {
  it("I in C octave 4 = 60", () => expect(scaleDegreePitch("I", "C", 4)).toBe(60));
  it("V in C octave 4 = 67", () => expect(scaleDegreePitch("V", "C", 4)).toBe(67));
  it("bVII in C octave 4 = 70", () => expect(scaleDegreePitch("bVII", "C", 4)).toBe(70));
});

describe("parseMeasure", () => {
  const ts44 = { numerator: 4, denominator: 4 };

  it("two-chord doubling C^7 D-7 → 4 beats", () => {
    const result = parseMeasure(1, ts44, "C^7 D-7");
    expect(result.beat_containers).toHaveLength(4);
    expect(result.beat_containers[0]?.chord.root).toBe("C");
    expect(result.beat_containers[1]?.chord.root).toBe("C");
    expect(result.beat_containers[2]?.chord.root).toBe("D");
    expect(result.beat_containers[3]?.chord.root).toBe("D");
  });

  it("empty measure → all null", () => {
    const result = parseMeasure(2, ts44, "");
    expect(result.beat_containers).toHaveLength(4);
    expect(result.beat_containers.every((b) => b === null)).toBe(true);
  });

  it("trailing delimiter → pads", () => {
    const result = parseMeasure(4, ts44, "C^7 ");
    expect(result.beat_containers).toHaveLength(4);
    expect(result.beat_containers.every((b) => b?.chord.root === "C")).toBe(true);
  });

  it("literal percent throws", () => {
    expect(() => parseMeasure(5, ts44, "F^7 % Eh A7")).toThrow();
  });

  it("6/8 two chords → 8 beats", () => {
    const result = parseMeasure(6, { numerator: 6, denominator: 8 }, "C^7 D-7");
    expect(result.beat_containers).toHaveLength(8);
  });

  it("overfull 3 chords → 5 beats (no pad)", () => {
    const result = parseMeasure(7, ts44, "F^7 Eh A7");
    expect(result.beat_containers).toHaveLength(5);
  });

  it("beat_location.measure_number matches m_number", () => {
    const result = parseMeasure(42, ts44, "C^7 D-7");
    expect(result.m_number).toBe(42);
    expect(result.beat_containers[0]?.beat_location.measure_number).toBe(42);
    expect(result.beat_containers[2]?.beat_location.measure_number).toBe(42);
  });

  it("beat_location.beat_number increments per beat", () => {
    const result = parseMeasure(1, ts44, "C^7 D-7");
    expect(result.beat_containers[0]?.beat_location.beat_number).toBe(0);
    expect(result.beat_containers[1]?.beat_location.beat_number).toBe(1);
    expect(result.beat_containers[2]?.beat_location.beat_number).toBe(2);
    expect(result.beat_containers[3]?.beat_location.beat_number).toBe(3);
  });

  it("time_signature stored in result", () => {
    const result = parseMeasure(1, ts44, "C^7");
    expect(result.time_signature).toEqual(ts44);
  });

  it("invalid chord string throws InvalidChordStringError", () => {
    expect(() => parseMeasure(1, ts44, "ZZZZZ")).toThrow(InvalidChordStringError);
  });
});
