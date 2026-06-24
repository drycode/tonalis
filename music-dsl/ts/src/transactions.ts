/**
 * transactions.ts — key-context operations: modulate, isDiatonic,
 * harmonicFunctionInKey, chordInKey.
 *
 * Port of music_dsl/transactions.py (Python reference).
 */

import { TWELVE_TONES, noteIndex } from "./notes.js";
import { SCALE_DEGREES, type ScaleDegreeT } from "./scaleDegree.js";
import {
  Triad,
  HarmonicFunction,
} from "./chordQuality.js";
import { Scales, encodingValue } from "./encode.js";
import { stripLeft, stripRight } from "./helpers.js";
import { semitonesApartAscending } from "./helpers.js";
import { type ChordModel, type ChordSerialized, parseChord, serializeChord } from "./chord.js";
import { fromChordString } from "./numericChord.js";
import {
  sdToFlat, sdToSharp, sdToMajor, sdToMinor,
  sdIsFlat, sdIsMinor, sdNormalize, sdGetIndex,
} from "./scaleDegreeHelpers.js";

/** True if the string matches a roman numeral pattern (scale degree). */
function isScaleDegree(value: string): boolean {
  return /^[b#]?[ivVI]{1,4}$/.test(value);
}

/** Unified get_index (Notes or ScaleDegree), mirrors Python get_index. */
function getIndex(note: string): number {
  return isScaleDegree(note) ? sdGetIndex(note) : noteIndex(note);
}

// ---------------------------------------------------------------------------
// Chord encoding helpers (value → name reverse maps)
// ---------------------------------------------------------------------------

function triadNameFromValue(value: string): string {
  const map: Record<string, string> = {
    "": "Major", "-": "Minor", "h": "HalfDiminished", "o": "Diminished",
    "+": "Augmented", "sus": "Sus", "sus2": "Sus2", "sus4": "Sus4",
  };
  const name = map[value];
  if (name === undefined) throw new Error(`Unknown triad value: ${value}`);
  return name;
}

function seventhNameFromValue(value: string): string {
  const map: Record<string, string> = { "^7": "Major", "7": "Minor", "": "_None" };
  const name = map[value];
  if (name === undefined) throw new Error(`Unknown seventh value: ${value}`);
  return name;
}

function extensionNameFromValue(value: string): string {
  const map: Record<string, string> = {
    "": "_None", "2": "add2", "3": "add3", "b5": "b5", "5": "add5",
    "#5": "s5", "b6": "b6", "6": "add6", "b9": "b9", "9": "add9",
    "#9": "s9", "11": "add11", "#11": "s11", "b13": "b13", "13": "add13", "alt": "alt",
  };
  const name = map[value];
  if (name === undefined) throw new Error(`Unknown extension value: ${value}`);
  return name;
}

/** Compute the chord's encoding bigint (mirrors chord.encoding in Python). */
function computeEncoding(chord: ChordModel): bigint {
  const triadName = triadNameFromValue(chord.triad);
  const seventhName = seventhNameFromValue(chord.seventh);
  const extNames = chord.extensions.map(extensionNameFromValue);
  return encodingValue(triadName, seventhName, extNames);
}

// ---------------------------------------------------------------------------
// bigint bit-length helper
// ---------------------------------------------------------------------------

function bigintBitLength(n: bigint): number {
  if (n === 0n) return 0;
  let len = 0;
  let v = n;
  while (v > 0n) { v >>= 1n; len++; }
  return len;
}

// ---------------------------------------------------------------------------
// modulate — mirrors Python transactions.modulate
// ---------------------------------------------------------------------------

/**
 * Transpose a note or scale degree by `semitones` steps.
 *
 * Notes path:        TWELVE_TONES[(noteIndex(note) + semitones) % 12]
 * ScaleDegree path:  SCALE_DEGREES[(sdGetIndex(d) + semitones) % 12].normalize(is_flat, is_minor)
 */
export function modulate(semitones: number, note: string): string {
  const idx = getIndex(note);
  const newIdx = ((idx + semitones) % 12 + 12) % 12;

  if (isScaleDegree(note)) {
    const base = SCALE_DEGREES[newIdx]!;
    return sdNormalize(base, sdIsFlat(note), sdIsMinor(note));
  }

  return TWELVE_TONES[newIdx] as string;
}

// ---------------------------------------------------------------------------
// isDiatonic — mirrors Python transactions.is_diatonic (healthy gated version)
// ---------------------------------------------------------------------------

/**
 * Determine if a chord encoding matches the target scale at the modal distance
 * from the root.
 *
 * Gates on _root_is_diatonic first (if root not in scale → false immediately).
 * Only then strips the scale to align with the chord encoding.
 *
 * @param root   - Note value string ("C", "Ab", …)
 * @param scale  - Scale name string ("Major", "Minor", "HarmonicMinor")
 * @param chord  - Parsed ChordModel
 */
export function isDiatonic(root: string, scale: string, chord: ChordModel): boolean {
  const scaleValue = Scales[scale];
  if (scaleValue === undefined) throw new Error(`Unknown scale: ${scale}`);

  const encoding = computeEncoding(chord);

  function getLeastSignificantNotePosition(): number {
    let y = encoding - 1n;
    let x = 0;
    while (y & 1n) { y >>= 1n; x++; }
    return x;
  }

  function rootIsDiatonic(scaleVal: bigint, scaleLength: number, semi: number): boolean {
    return !!(scaleVal & (1n << BigInt(scaleLength - semi - 1)));
  }

  const semitones = semitonesApartAscending(root, chord.root);
  const scaleLength = bigintBitLength(scaleValue);

  if (rootIsDiatonic(scaleValue, scaleLength, semitones)) {
    const lsnp = getLeastSignificantNotePosition();
    const chordBits = stripRight(encoding, lsnp);
    const modalScale = stripLeft(scaleValue, semitones);
    const scaleBits = stripRight(
      modalScale,
      bigintBitLength(modalScale) - bigintBitLength(chordBits),
    );
    if ((chordBits & scaleBits) === chordBits) {
      return true;
    }
  }

  return false;
}

// ---------------------------------------------------------------------------
// harmonicFunctionInKey — mirrors Python transactions.harmonic_function_in_key
// ---------------------------------------------------------------------------

/**
 * Determine a chord's harmonic function relative to a key center.
 *
 * Key-dependent rule: a minor-7 chord on the tonic scale degree in a minor key
 * is Tonic (overrides the quality-based Subdominant label).
 * Blues I7 and all other chords keep their quality-based function.
 */
export function harmonicFunctionInKey(
  keyRoot: string,
  keyIsMinor: boolean,
  chord: ChordModel,
): string {
  const degree = semitonesApartAscending(keyRoot, chord.root);
  if (degree === 0 && keyIsMinor && chord.triad === Triad.Minor) {
    return HarmonicFunction.Tonic;
  }
  return chord.harmonic_function;
}

// ---------------------------------------------------------------------------
// qualitySuffix — mirrors Python transactions._quality_suffix
// Builds a chord-parseable suffix from the numeric chord's quality values.
// ---------------------------------------------------------------------------

function qualitySuffix(triad: string, seventh: string, extensions: string[]): string {
  return triad + seventh + extensions.join("");
}

// ---------------------------------------------------------------------------
// chordInKey — mirrors Python transactions.chord_in_key
// ---------------------------------------------------------------------------

/**
 * Realize a key-relative numeric chord string into an absolute ChordSerialized.
 *
 * Slash chords resolve recursively:
 *   denominator root: modulate(getIndex(denom.root), keyRoot)
 *   numerator root:   modulate(getIndex(num.root), denominatorAbsRoot)
 */
export function chordInKey(numericStr: string, keyRoot: string): ChordSerialized {
  const numeric = fromChordString(numericStr);
  const { numerator, denominator } = numeric;

  let absRoot: string;
  if (denominator) {
    const denomRoot = modulate(getIndex(denominator.root), keyRoot);
    absRoot = modulate(getIndex(numerator.root), denomRoot);
  } else {
    absRoot = modulate(getIndex(numerator.root), keyRoot);
  }

  const suffix = qualitySuffix(numerator.triad, numerator.seventh, numerator.extensions);
  const chordStr = absRoot + suffix;
  const chord = parseChord(chordStr);
  return serializeChord(chord);
}
