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

/** minor → major: lowercase roman numeral → uppercase (accidental preserved). */
const MINOR_TO_MAJOR: Readonly<Record<string, ScaleDegreeT>> = {
  "i": "I", "#i": "#I", "bii": "bII", "ii": "II", "#ii": "#II",
  "biii": "bIII", "iii": "III", "iv": "IV", "#iv": "#IV",
  "bv": "bV", "v": "V", "#v": "#V", "bvi": "bVI", "vi": "VI",
  "#vi": "#VI", "bvii": "bVII", "vii": "VII",
};

/** major → minor: inverse of MINOR_TO_MAJOR. */
const MAJOR_TO_MINOR: Readonly<Record<string, ScaleDegreeT>> = {
  "I": "i", "#I": "#i", "bII": "bii", "II": "ii", "#II": "#ii",
  "bIII": "biii", "III": "iii", "IV": "iv", "#IV": "#iv",
  "bV": "bv", "V": "v", "#V": "#v", "bVI": "bvi", "VI": "vi",
  "#VI": "#vi", "bVII": "bvii", "VII": "vii",
};

// ---------------------------------------------------------------------------
// Scale-degree primitives (single source of truth; formerly duplicated in
// scaleDegreeHelpers.ts and, map-vs-regex-divergently, inline below).
// Mirror the Python ScaleDegree.to_flat / to_sharp / to_major / to_minor /
// normalize / get_index methods.
// ---------------------------------------------------------------------------

/** to_flat(): sharp → flat enharmonic; pass through otherwise. */
export function sdToFlat(d: string): ScaleDegreeT {
  return (SHARPS_TO_FLATS[d] ?? d) as ScaleDegreeT;
}

/** to_sharp(): flat → sharp enharmonic; pass through otherwise. */
export function sdToSharp(d: string): ScaleDegreeT {
  return (FLATS_TO_SHARPS[d] ?? d) as ScaleDegreeT;
}

/** to_major(): minor → major; pass through otherwise. */
export function sdToMajor(d: string): ScaleDegreeT {
  return (MINOR_TO_MAJOR[d] ?? d) as ScaleDegreeT;
}

/** to_minor(): major → minor; pass through otherwise. */
export function sdToMinor(d: string): ScaleDegreeT {
  return (MAJOR_TO_MINOR[d] ?? d) as ScaleDegreeT;
}

/** is_flat: true iff the degree carries a flat accidental. */
export function sdIsFlat(d: string): boolean {
  return d in FLATS_TO_SHARPS;
}

/** is_minor: true iff the degree is a lowercase (minor) numeral. */
export function sdIsMinor(d: string): boolean {
  return d in MINOR_TO_MAJOR;
}

/**
 * normalize(is_flat, is_minor) — mirror of Python ScaleDegree.normalize.
 * to_flat() if is_flat else to_sharp(), then to_minor() if is_minor else to_major().
 */
export function sdNormalize(d: string, isFlat: boolean, isMinor: boolean): ScaleDegreeT {
  let r: ScaleDegreeT = isFlat ? sdToFlat(d) : sdToSharp(d);
  r = isMinor ? sdToMinor(r) : sdToMajor(r);
  return r;
}

/** get_index: SCALE_DEGREES.indexOf(d.to_major().to_flat()). */
export function sdGetIndex(d: string): number {
  const idx = SCALE_DEGREES.indexOf(sdToFlat(sdToMajor(d)));
  if (idx === -1) throw new Error(`Unknown scale degree for get_index: ${d}`);
  return idx;
}

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
  const idx = SCALE_DEGREES.indexOf(sdToFlat(sdToMajor(value)));
  if (idx === -1) throw new Error(`Unknown scale degree: ${value}`);
  return idx;
}
