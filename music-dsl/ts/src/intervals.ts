/**
 * Intervals — 13 named interval semitone values.
 * Port of music_dsl/domain/static/intervals.py (Python reference).
 * Lookup is by member NAME (e.g. "m6"), value is the semitone count.
 */

/** The 13 interval names (member names in the Python IntEnum). */
export type IntervalName =
  | "Unison" | "m2" | "M2" | "m3" | "M3" | "P4"
  | "Tritone" | "P5" | "m6" | "M6" | "m7" | "M7" | "Octave";

/** Map from interval member name → semitone count. */
const INTERVAL_SEMITONES_MAP: Readonly<Record<IntervalName, number>> = {
  Unison: 0,
  m2: 1,
  M2: 2,
  m3: 3,
  M3: 4,
  P4: 5,
  Tritone: 6,
  P5: 7,
  m6: 8,
  M6: 9,
  m7: 10,
  M7: 11,
  Octave: 12,
};

/**
 * Return the semitone count for a named interval.
 * Lookup is by member NAME (e.g. "m6" → 8).
 */
export function intervalSemitones(name: string): number {
  const s = INTERVAL_SEMITONES_MAP[name as IntervalName];
  if (s === undefined) throw new Error(`Unknown interval name: ${name}`);
  return s;
}

/**
 * Plain integer equality on semitone values.
 * Mirrors Intervals.__eq__ (int equality — m6 != M3 since 8 != 4).
 */
export function intervalsEqual(a: string, b: string): boolean {
  return intervalSemitones(a) === intervalSemitones(b);
}
