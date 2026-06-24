/**
 * measure.ts — time-aware chord containers (measure / beat).
 * Port of music_dsl/time/measure.py
 */

import { parseChord, serializeChord, InvalidChordStringError, type ChordSerialized } from "./chord.js";

// ---------------------------------------------------------------------------
// Public interfaces
// ---------------------------------------------------------------------------

export interface TimeSignature {
  numerator: number;
  denominator: number;
}

export interface BeatLocation {
  measure_number: number;
  beat_number: number;
}

export interface BeatContainer {
  beat_location: BeatLocation;
  chord: ChordSerialized;
}

export interface MeasureModel {
  m_number: number;
  time_signature: TimeSignature;
  beat_containers: (BeatContainer | null)[];
}

// ---------------------------------------------------------------------------
// countChar — count occurrences of a char in a string
// ---------------------------------------------------------------------------

function countChar(s: string, ch: string): number {
  let count = 0;
  for (const c of s) {
    if (c === ch) count++;
  }
  return count;
}

// ---------------------------------------------------------------------------
// serializeMeasure — build the MeasureModel from beats array
// ---------------------------------------------------------------------------

export function serializeMeasure(
  mNumber: number,
  timeSignature: TimeSignature,
  beats: (ChordSerialized | null)[],
): MeasureModel {
  return {
    m_number: mNumber,
    time_signature: timeSignature,
    beat_containers: beats.map((chord, beatNumber) => {
      if (chord === null) return null;
      return {
        beat_location: { measure_number: mNumber, beat_number: beatNumber },
        chord,
      };
    }),
  };
}

// ---------------------------------------------------------------------------
// parseMeasure — _setup_beats algorithm (port of Python reference)
// ---------------------------------------------------------------------------

/**
 * Parse a raw measure string into a MeasureModel.
 *
 * Algorithm (_setup_beats):
 * 1. Tokenize: replace every space with "% " then split on " ".
 *    Pop trailing empty strings.
 * 2. Count total beats: each token contributes 1 + count('%') beats.
 * 3. size = max(timeSignature.denominator, totalBeats)
 * 4. Fill: for each token, strip all '%' to get chordStr.
 *    If chordStr is empty (literal "%" token) → throw InvalidChordStringError.
 *    Otherwise parseChord(chordStr), write to `slots = 1 + count('%')` positions.
 * 5. Pad remaining positions with lastChord (null if no chords were parsed).
 *
 * Throws InvalidChordStringError on invalid chord strings or bare "%" tokens.
 */
export function parseMeasure(
  mNumber: number,
  timeSignature: TimeSignature,
  rawMeasure: string,
): MeasureModel {
  // Step 1: tokenize
  const chordsList = rawMeasure.replaceAll(" ", "% ").split(" ");
  // Pop trailing empty strings
  while (chordsList.length > 0 && chordsList[chordsList.length - 1] === "") {
    chordsList.pop();
  }

  // Step 2: total beats
  const totalBeats = chordsList.reduce((sum: number, tok: string) => sum + 1 + countChar(tok, "%"), 0);

  // Step 3: size
  const size = Math.max(timeSignature.denominator, totalBeats);

  // Step 4: fill beats array
  const beats: (ChordSerialized | null)[] = new Array(size).fill(null);
  let lastChord: ChordSerialized | null = null;
  let pos = 0;

  for (const tok of chordsList) {
    const chordStr = tok.replaceAll("%", ""); // strip all %
    if (chordStr === "") {
      // Literal "%" token → empty chord string → invalid
      throw new InvalidChordStringError('Empty chord string from literal "%"');
    }
    const chord = parseChord(chordStr); // may throw InvalidChordStringError
    const serialized = serializeChord(chord);
    lastChord = serialized;
    const slots = 1 + countChar(tok, "%");
    for (let s = 0; s < slots; s++) {
      beats[pos++] = serialized;
    }
  }

  // Step 5: pad remaining with lastChord (null if no chords)
  while (pos < size) {
    beats[pos++] = lastChord;
  }

  return serializeMeasure(mNumber, timeSignature, beats);
}
