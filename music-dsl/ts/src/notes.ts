/**
 * Notes — 17 chromatic spellings with enharmonic equality.
 * Port of music_dsl/domain/static/notes.py (Python reference).
 */

/** The 17 chromatic spelling strings. */
export type Note =
  | "C" | "C#" | "Db" | "D" | "D#" | "Eb" | "E" | "F"
  | "F#" | "Gb" | "G" | "G#" | "Ab" | "A" | "A#" | "Bb" | "B";

/** Canonical flat-spelled chromatic scale, index 0–11 (TWELVE_TONES). */
export const TWELVE_TONES: readonly Note[] = [
  "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B",
];

/** Sharp → flat enharmonic pairs (5 pairs). */
const SHARPS_TO_FLATS: Readonly<Record<string, Note>> = {
  "C#": "Db",
  "D#": "Eb",
  "F#": "Gb",
  "G#": "Ab",
  "A#": "Bb",
};

/** Flat → sharp enharmonic pairs (inverse of SHARPS_TO_FLATS). */
const FLATS_TO_SHARPS: Readonly<Record<string, Note>> = {
  "Db": "C#",
  "Eb": "D#",
  "Gb": "F#",
  "Ab": "G#",
  "Bb": "A#",
};

/** Chromatic index 0–11 per spelling (TO_C table). */
const NOTE_INDEX_MAP: Readonly<Record<string, number>> = {
  "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
  "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
  "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
};

/** Return the string value of a Note (identity — Notes are their own values). */
export function noteValue(n: Note): string {
  return n;
}

/** Parse a string into a Note, throwing if not a valid spelling. */
export function noteFromValue(v: string): Note {
  if (NOTE_INDEX_MAP[v] !== undefined) return v as Note;
  throw new Error(`Unknown note spelling: ${v}`);
}

/**
 * Normalize a sharp spelling to its flat enharmonic; all other spellings pass through.
 * Mirrors Notes.to_flat() / Notes.normalized().
 */
export function noteToFlat(n: Note | string): Note {
  const flat = SHARPS_TO_FLATS[n];
  return flat ?? (n as Note);
}

/**
 * Enharmonic equality: true iff same spelling, or one maps to the other via
 * sharps_to_flats / flats_to_sharps. Mirrors Notes.__eq__ from the reference.
 */
export function notesEqual(a: string, b: string): boolean {
  if (a === b) return true;
  // a is sharp → b must be its flat equivalent
  const aFlat = SHARPS_TO_FLATS[a];
  if (aFlat !== undefined && aFlat === b) return true;
  // a is flat → b must be its sharp equivalent
  const aSharp = FLATS_TO_SHARPS[a];
  if (aSharp !== undefined && aSharp === b) return true;
  // b is sharp → a must be its flat equivalent
  const bFlat = SHARPS_TO_FLATS[b];
  if (bFlat !== undefined && bFlat === a) return true;
  // b is flat → a must be its sharp equivalent
  const bSharp = FLATS_TO_SHARPS[b];
  if (bSharp !== undefined && bSharp === a) return true;
  return false;
}

/**
 * Chromatic index 0–11 for a note spelling (via TO_C table).
 * Mirrors helpers.get_index(Notes(value)) for all 17 spellings.
 */
export function noteIndex(value: string): number {
  const idx = NOTE_INDEX_MAP[value];
  if (idx === undefined) throw new Error(`Unknown note spelling: ${value}`);
  return idx;
}
