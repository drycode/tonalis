/**
 * scaleDegreeHelpers.ts — shared ScaleDegree utilities.
 *
 * Extracted from transactions.ts and numericChord.ts (genuine copy-paste duplication).
 * Both files use the same four helpers and the same SHARPS_TO_FLATS / FLATS_TO_SHARPS maps;
 * the only difference was the return type annotation (string vs ScaleDegreeT) — we use
 * ScaleDegreeT throughout since it is a branded string (assignable to string).
 */

import { SCALE_DEGREES, type ScaleDegreeT } from "./scaleDegree.js";

// ---------------------------------------------------------------------------
// Enharmonic / case conversion maps
// ---------------------------------------------------------------------------

export const SHARPS_TO_FLATS: Readonly<Record<string, ScaleDegreeT>> = {
  "#I": "bII", "#i": "bii", "#II": "bIII", "#ii": "biii",
  "#IV": "bV", "#iv": "bv", "#V": "bVI", "#v": "bvi",
  "#VI": "bVII", "#vi": "bvii",
};

export const FLATS_TO_SHARPS: Readonly<Record<string, ScaleDegreeT>> = {
  "bII": "#I", "bii": "#i", "bIII": "#II", "biii": "#ii",
  "bV": "#IV", "bv": "#iv", "bVI": "#V", "bvi": "#v",
  "bVII": "#VI", "bvii": "#vi",
};

const MINOR_TO_MAJOR: Readonly<Record<string, ScaleDegreeT>> = {
  "i": "I", "#i": "#I", "bii": "bII", "ii": "II", "#ii": "#II",
  "biii": "bIII", "iii": "III", "iv": "IV", "#iv": "#IV",
  "bv": "bV", "v": "V", "#v": "#V", "bvi": "bVI", "vi": "VI",
  "#vi": "#VI", "bvii": "bVII", "vii": "VII",
};

const MAJOR_TO_MINOR: Readonly<Record<string, ScaleDegreeT>> = {
  "I": "i", "#I": "#i", "bII": "bii", "II": "ii", "#II": "#ii",
  "bIII": "biii", "III": "iii", "IV": "iv", "#IV": "#iv",
  "bV": "bv", "V": "v", "#V": "#v", "bVI": "bvi", "VI": "vi",
  "#VI": "#vi", "bVII": "bvii", "VII": "vii",
};

// ---------------------------------------------------------------------------
// Shared helpers (mirror Python ScaleDegree.to_flat / to_sharp / normalize / get_index)
// ---------------------------------------------------------------------------

export function sdToFlat(d: string): ScaleDegreeT {
  return (SHARPS_TO_FLATS[d] ?? d) as ScaleDegreeT;
}

export function sdToSharp(d: string): ScaleDegreeT {
  return (FLATS_TO_SHARPS[d] ?? d) as ScaleDegreeT;
}

export function sdToMajor(d: string): ScaleDegreeT {
  return (MINOR_TO_MAJOR[d] ?? d) as ScaleDegreeT;
}

export function sdToMinor(d: string): ScaleDegreeT {
  return (MAJOR_TO_MINOR[d] ?? d) as ScaleDegreeT;
}

export function sdIsFlat(d: string): boolean {
  return d in FLATS_TO_SHARPS;
}

export function sdIsMinor(d: string): boolean {
  return d in MINOR_TO_MAJOR;
}

/**
 * normalize(is_flat, is_minor) — mirror of Python ScaleDegree.normalize.
 * to_flat() if is_flat else to_sharp(), then to_minor() if is_minor else to_major()
 */
export function sdNormalize(d: string, isFlat: boolean, isMinor: boolean): ScaleDegreeT {
  let r: ScaleDegreeT = isFlat ? sdToFlat(d) : sdToSharp(d);
  r = isMinor ? sdToMinor(r) : sdToMajor(r);
  return r;
}

/**
 * get_index for a ScaleDegree: SCALE_DEGREES.indexOf(d.to_major().to_flat())
 * Mirrors Python ScaleDegree.get_index.
 */
export function sdGetIndex(d: string): number {
  const major = sdToMajor(d);
  const flat = sdToFlat(major);
  const idx = SCALE_DEGREES.indexOf(flat as ScaleDegreeT);
  if (idx === -1) throw new Error(`Unknown scale degree for get_index: ${d}`);
  return idx;
}
