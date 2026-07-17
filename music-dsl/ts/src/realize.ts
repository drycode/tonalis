/**
 * realize.ts — MIDI pitch realization for notes, intervals, chords, scales, scale degrees.
 * Port of music_dsl/realize.py
 */

import { intervalSemitones } from "./intervals.js";
import { Scales } from "./encode.js";
import { parseChord, type ChordModel } from "./chord.js";
import { Triad, Seventh } from "./chordQuality.js";
import { scaleDegreeIndex } from "./scaleDegree.js";
import { modulate } from "./transactions.js";
import { semitonesApartAscending, bigintBitLength } from "./helpers.js";

// ---------------------------------------------------------------------------
// Realize-internal encoding maps keyed by chord VALUE (not member NAME)
// ---------------------------------------------------------------------------

/** Triad value → semitone offsets */
const TRIAD_OFFSETS: Readonly<Record<string, readonly number[]>> = {
  "":     [4, 7],  // Major
  "-":    [3, 7],  // Minor
  "h":    [3, 6],  // HalfDiminished
  "o":    [3, 6],  // Diminished
  "+":    [4, 8],  // Augmented
  "sus":  [5, 7],  // Sus
  "sus2": [2, 7],  // Sus2
  "sus4": [5, 7],  // Sus4
} as const;

/** Seventh value → semitone offsets (default; dim7 overrides "7" → [9]) */
const SEVENTH_OFFSETS: Readonly<Record<string, readonly number[]>> = {
  "^7": [11],  // Major seventh
  "7":  [10],  // Minor seventh
  "":   [],    // None
} as const;

/** Extension value → semitone offsets */
const EXTENSION_OFFSETS: Readonly<Record<string, readonly number[]>> = {
  "":    [],
  "2":   [2],
  "3":   [4],
  "b5":  [6],
  "5":   [7],
  "#5":  [8],
  "b6":  [8],
  "6":   [9],
  "b9":  [12],
  "9":   [13],
  "#9":  [14],
  "11":  [15],
  "#11": [16],
  "b13": [17],
  "13":  [18],
  "alt": [12, 14, 16, 17],
} as const;

// ---------------------------------------------------------------------------
// noteToMidi
// ---------------------------------------------------------------------------

/**
 * Convert a note name and octave to a MIDI pitch number.
 * Middle C (C4) = 60, A4 = 69.
 */
export function noteToMidi(note: string, octave: number): number {
  const pitchClass = semitonesApartAscending("C", note);
  return 12 * (octave + 1) + pitchClass;
}

// ---------------------------------------------------------------------------
// midiToHz
// ---------------------------------------------------------------------------

/**
 * Convert a MIDI pitch number to frequency in Hz (A4=440).
 * Result is rounded to 4 decimal places.
 */
export function midiToHz(midi: number): number {
  const hz = 440 * Math.pow(2, (midi - 69) / 12);
  return Math.round(hz * 1e4) / 1e4;
}

// ---------------------------------------------------------------------------
// intervalPitches
// ---------------------------------------------------------------------------

/**
 * Return the two MIDI pitches forming an interval above `root` at `octave`.
 */
export function intervalPitches(root: string, interval: string, octave: number): number[] {
  const base = noteToMidi(root, octave);
  return [base, base + intervalSemitones(interval)];
}

// ---------------------------------------------------------------------------
// chordPitches
// ---------------------------------------------------------------------------

/**
 * Return the sorted MIDI pitches for a chord (string or ChordModel) at `octave`.
 *
 * dim7 rule: Diminished triad + minor seventh → seventh offset = [9] (not [10]).
 *   Co7 → [60,63,66,69]; Ch7 → [60,63,66,70].
 */
export function chordPitches(chord: ChordModel | string, octave: number): number[] {
  const c: ChordModel = typeof chord === "string" ? parseChord(chord) : chord;

  const triadOffsets = TRIAD_OFFSETS[c.triad];
  if (triadOffsets === undefined) throw new Error(`Unknown triad value: ${c.triad}`);

  // dim7 rule: fully-diminished seventh (o + 7) → offsets [9] instead of [10]
  let seventhOffsets: readonly number[];
  if (c.triad === Triad.Diminished && c.seventh === Seventh.Minor) {
    seventhOffsets = [9];
  } else {
    const raw = SEVENTH_OFFSETS[c.seventh];
    if (raw === undefined) throw new Error(`Unknown seventh value: ${c.seventh}`);
    seventhOffsets = raw;
  }

  // Collect extension offsets
  const extOffsets: number[] = [];
  for (const ext of c.extensions) {
    const offs = EXTENSION_OFFSETS[ext];
    if (offs === undefined) throw new Error(`Unknown extension value: ${ext}`);
    extOffsets.push(...offs);
  }

  // Merge all offsets (root=0 always included)
  const allOffsets = new Set([0, ...triadOffsets, ...seventhOffsets, ...extOffsets]);
  const sorted = [...allOffsets].sort((a, b) => a - b);

  const base = noteToMidi(c.root, octave);
  return sorted.map((o) => base + o);
}

// ---------------------------------------------------------------------------
// scalePitches
// ---------------------------------------------------------------------------

/**
 * Return the MIDI pitches for a named scale starting at `keyRoot` in `octave`.
 * Always appends the octave note as the final pitch.
 *
 * IMPORTANT: Uses BigInt arithmetic throughout — the 36-bit Scales values exceed
 * 32-bit JS bitwise operator range. All >> and & operations use BigInt.
 */
export function scalePitches(keyRoot: string, scale: string, octave: number): number[] {
  const value = Scales[scale];
  if (value === undefined) throw new Error(`Unknown scale: ${scale}`);

  const bitLen = bigintBitLength(value);
  const size = Math.floor(bitLen / 3); // e.g. 36 / 3 = 12

  // Top 12-bit pattern = value >> (2 * size) — bits 24–35 of the 36-bit value.
  // Must use BigInt >> to avoid 32-bit truncation.
  const top = value >> BigInt(2 * size);

  const base = noteToMidi(keyRoot, octave);
  const result: number[] = [];

  for (let i = 0; i < size; i++) {
    // Bit i is at position (size - 1 - i) in `top` (MSB = index 0)
    if ((top >> BigInt(size - 1 - i)) & 1n) {
      result.push(base + i);
    }
  }

  // Always append octave
  result.push(base + size);
  return result;
}

// ---------------------------------------------------------------------------
// scaleDegreePitch
// ---------------------------------------------------------------------------

/**
 * Return the MIDI pitch for a scale degree in a given key and octave.
 * Mirrors Python realize.scale_degree_pitch.
 */
export function scaleDegreePitch(degree: string, keyRoot: string, octave: number): number {
  const idx = scaleDegreeIndex(degree);
  const note = modulate(idx, keyRoot);
  return noteToMidi(note, octave);
}
