/**
 * ScaleDegree — 34 named scale degrees with enharmonic equality.
 * Port of music_dsl/domain/static/scale_degree.py (Python reference).
 * Lookup is by VALUE (e.g. "#iv", "bII").
 */

/** All 34 scale degree value strings. */
export type ScaleDegreeT =
  | "I" | "i" | "#I" | "#i" | "bII" | "bii" | "II" | "ii"
  | "#II" | "#ii" | "bIII" | "biii" | "III" | "iii"
  | "IV" | "iv" | "#IV" | "#iv" | "bV" | "bv" | "V" | "v"
  | "#V" | "#v" | "bVI" | "bvi" | "VI" | "vi"
  | "#VI" | "#vi" | "bVII" | "bvii" | "VII" | "vii";

/** sharps_to_flats: 10 pairs (major and minor variants). */
const SHARPS_TO_FLATS: Readonly<Record<string, ScaleDegreeT>> = {
  "#I":  "bII",
  "#i":  "bii",
  "#II": "bIII",
  "#ii": "biii",
  "#IV": "bV",
  "#iv": "bv",
  "#V":  "bVI",
  "#v":  "bvi",
  "#VI": "bVII",
  "#vi": "bvii",
};

/** flats_to_sharps: inverse of SHARPS_TO_FLATS. */
const FLATS_TO_SHARPS: Readonly<Record<string, ScaleDegreeT>> = {
  "bII":  "#I",
  "bii":  "#i",
  "bIII": "#II",
  "biii": "#ii",
  "bV":   "#IV",
  "bv":   "#iv",
  "bVI":  "#V",
  "bvi":  "#v",
  "bVII": "#VI",
  "bvii": "#vi",
};

/**
 * Enharmonic equality for scale degrees.
 * #iv == bv (same pitch class), but major/minor remain distinct (II != ii).
 * Mirrors ScaleDegree.__eq__ from the reference.
 */
export function scaleDegreesEqual(a: string, b: string): boolean {
  if (a === b) return true;
  const aFlat = SHARPS_TO_FLATS[a];
  if (aFlat !== undefined && aFlat === b) return true;
  const aSharp = FLATS_TO_SHARPS[a];
  if (aSharp !== undefined && aSharp === b) return true;
  const bFlat = SHARPS_TO_FLATS[b];
  if (bFlat !== undefined && bFlat === a) return true;
  const bSharp = FLATS_TO_SHARPS[b];
  if (bSharp !== undefined && bSharp === a) return true;
  return false;
}

/** Canonical flat-major scale degrees, index 0–11 (SCALE_DEGREES). */
export const SCALE_DEGREES: readonly ScaleDegreeT[] = [
  "I", "bII", "II", "bIII", "III", "IV",
  "bV", "V", "bVI", "VI", "bVII", "VII",
];

/** Return the scale degree's index in SCALE_DEGREES (after to_major().to_flat()). */
export function scaleDegreeIndex(value: string): number {
  // Convert to major if minor
  const major = toMajorDegree(value);
  // Normalize to flat
  const flat = toFlatDegree(major);
  const idx = SCALE_DEGREES.indexOf(flat as ScaleDegreeT);
  if (idx === -1) throw new Error(`Unknown scale degree: ${value}`);
  return idx;
}

/** Map minor → major (lowercase → uppercase roman numeral part). */
function toMajorDegree(value: string): string {
  // Replace the roman numeral part (after prefix) with uppercase
  return value.replace(/([ivxIVX]+)/, (m) => m.toUpperCase());
}

/** Normalize a sharp degree to its flat enharmonic; pass through otherwise. */
function toFlatDegree(value: string): string {
  return SHARPS_TO_FLATS[value] ?? value;
}
