/**
 * encode — chord encoding + scale bit-vectors.
 * Port of music_dsl/encode.py using BigInt (Scales are 36-bit; JS << truncates at 32 bits).
 *
 * The Python reference keyed EncodingMap by enum TYPE (Triad.Minor ≠ Seventh.Minor).
 * Here we maintain three separate lookup maps by role (triad / seventh / extension)
 * so name collisions ("Minor" means [3,7] for a Triad but [10] for a Seventh) are
 * resolved by context, matching the Python reference exactly.
 */

import { bigintBitLength } from "./helpers.js";

/** Sentinel / root bit at position 18 (bit 18 of the 19-bit chord encoding). */
export const EMPTY_CHORD_ENCODING: bigint = 1n << 18n; // 262144n

/** Bit-length of the chord encoding vector (19 bits). */
const CHORD_ENCODING_BIT_LENGTH = 19;

/** Special-cased fully-diminished core encoding. */
export const DIMINISHED_ENCODING: bigint = 0b1001001001000000000n; // 299520n

// ---------------------------------------------------------------------------
// Separate maps keyed by member NAME, partitioned by role
// ---------------------------------------------------------------------------

/** Triad member name → semitone bit positions. */
const TRIAD_MAP: Readonly<Record<string, readonly number[]>> = {
  Major:          [4, 7],
  Minor:          [3, 7],
  Diminished:     [3, 6],
  HalfDiminished: [3, 6],
  Augmented:      [4, 8],
  Sus2:           [2, 7],
  Sus:            [5, 7],
  Sus4:           [5, 7],
} as const;

/** Seventh member name → semitone bit positions. */
const SEVENTH_MAP: Readonly<Record<string, readonly number[]>> = {
  Minor: [10],
  Major: [11],
  _None: [],
} as const;

/** Extension member name → semitone bit positions. */
const EXTENSION_MAP: Readonly<Record<string, readonly number[]>> = {
  _None: [],
  add2:  [2],
  add3:  [4],
  b5:    [6],
  add5:  [7],
  s5:    [8],
  b6:    [8],
  add6:  [9],
  b9:    [12],
  add9:  [13],
  s9:    [14],
  add11: [15],
  s11:   [16],
  b13:   [17],
  add13: [18],
  alt:   [12, 14, 16, 17],
} as const;

/** Internal: build a bigint bitmask from a list of semitone shift positions. */
function _encode(bitPositions: readonly number[]): bigint {
  if (bitPositions.length === 0) return 0n;
  let encoding = EMPTY_CHORD_ENCODING;
  for (const shift of bitPositions) {
    encoding |= 1n << BigInt(CHORD_ENCODING_BIT_LENGTH - (shift + 1));
  }
  return encoding;
}

/**
 * Compute the `value` integer for a chord encoding (port of Encoding.value).
 * Only triad, seventh, and extensions affect the integer; root/context do not.
 *
 * @param triad      - Triad member name ("Major", "Minor", …)
 * @param seventh    - Seventh member name ("Major", "Minor", "_None")
 * @param extensions - Extension member names (["b9", "add11", …])
 */
export function encodingValue(
  triad: string,
  seventh: string,
  extensions: readonly string[],
): bigint {
  const triadPositions = TRIAD_MAP[triad];
  if (triadPositions === undefined)
    throw new Error(`Unknown triad member name: ${triad}`);

  const seventhPositions = SEVENTH_MAP[seventh];
  if (seventhPositions === undefined)
    throw new Error(`Unknown seventh member name: ${seventh}`);

  // Special-case Diminished core (mirrors encode.py)
  const core =
    triad === "Diminished"
      ? DIMINISHED_ENCODING
      : _encode([...triadPositions, ...seventhPositions]);

  // Extensions: concatenate each extension's bit positions
  const extPositions: number[] = [];
  for (const ext of extensions) {
    const pos = EXTENSION_MAP[ext];
    if (pos === undefined) throw new Error(`Unknown extension member name: ${ext}`);
    extPositions.push(...pos);
  }
  const extsValue = _encode(extPositions);

  return core | extsValue;
}

// ---------------------------------------------------------------------------
// Scale catalog — the frozen cross-port contract (see SPEC-scales.md).
// ---------------------------------------------------------------------------

/**
 * Build a scale's 36-bit mask from its pitch classes (semitones above the tonic,
 * 0–11). The 12-bit pattern (MSB = tonic) is repeated 3× so the modal scan can
 * rotate to any root without the sliding window falling off the MSB end. Mirrors
 * Python `_scale_mask` — derive masks from pitch-class sets, never hand-write the
 * 36-bit literal.
 */
function _scaleMask(...pitchClasses: number[]): bigint {
  let pattern = 0n;
  for (const pc of pitchClasses) {
    pattern |= 1n << BigInt(11 - pc);
  }
  return (pattern << 24n) | (pattern << 12n) | pattern;
}

/**
 * Everything the library needs to know about a scale.
 *
 * `mask` is the 12-bit pitch-class set repeated 3× (36 bits) — the triple copy
 * lets the sliding-window scan rotate the scale to any mode/root.
 *
 * `supportsDiatonicFunction` drives the two-tier model: membership (`contains`)
 * is defined for every scale, but functional queries (`isDiatonic` / harmonic
 * function) are only meaningful where a tonal hierarchy exists. Symmetric/atonal
 * scales set this false and those queries refuse (throw) rather than return an
 * answer that looks authoritative but isn't.
 */
export interface ScaleDescriptor {
  readonly mask: bigint;
  readonly name: string;
  readonly category: string;
  readonly supportsDiatonicFunction: boolean;
}

/**
 * A functional query (diatonicity / harmonic function) was made against a scale
 * with no meaningful tonal-function model (whole-tone, diminished, augmented,
 * chromatic). Membership via `contains` still works for these — mirrors Python
 * `NonFunctionalScaleError`.
 */
export class NonFunctionalScaleError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NonFunctionalScaleError";
  }
}

/** A functional scale (has a tonal hierarchy; diatonic queries are defined). */
function _fn(mask: bigint, name: string, category: string): ScaleDescriptor {
  return { mask, name, category, supportsDiatonicFunction: true };
}

/** A symmetric/atonal scale (no tonal-function model; membership only). */
function _sym(mask: bigint, name: string, category: string): ScaleDescriptor {
  return { mask, name, category, supportsDiatonicFunction: false };
}

/**
 * The frozen 37-scale catalog. Each entry carries a full descriptor (mask + name
 * + category + two-tier flag). Masks are derived from pitch-class sets via
 * `_scaleMask` so they equal the blessed `scale_value` numbers exactly.
 * Mirrors the `Scales` enum in encode.py.
 */
export const Scales: Readonly<Record<string, ScaleDescriptor>> = {
  // --- Modes of the major scale (functional) --------------------------------
  Major:      _fn(_scaleMask(0, 2, 4, 5, 7, 9, 11), "Major (Ionian)", "major-mode"),
  Dorian:     _fn(_scaleMask(0, 2, 3, 5, 7, 9, 10), "Dorian", "major-mode"),
  Phrygian:   _fn(_scaleMask(0, 1, 3, 5, 7, 8, 10), "Phrygian", "major-mode"),
  Lydian:     _fn(_scaleMask(0, 2, 4, 6, 7, 9, 11), "Lydian", "major-mode"),
  Mixolydian: _fn(_scaleMask(0, 2, 4, 5, 7, 9, 10), "Mixolydian", "major-mode"),
  Minor:      _fn(_scaleMask(0, 2, 3, 5, 7, 8, 10), "Natural minor (Aeolian)", "major-mode"),
  Locrian:    _fn(_scaleMask(0, 1, 3, 5, 6, 8, 10), "Locrian", "major-mode"),

  // --- Melodic minor and its modes (functional) -----------------------------
  MelodicMinor:    _fn(_scaleMask(0, 2, 3, 5, 7, 9, 11), "Melodic minor", "melodic-minor"),
  DorianFlat2:     _fn(_scaleMask(0, 1, 3, 5, 7, 9, 10), "Dorian b2", "melodic-minor"),
  LydianAugmented: _fn(_scaleMask(0, 2, 4, 6, 8, 9, 11), "Lydian augmented", "melodic-minor"),
  LydianDominant:  _fn(_scaleMask(0, 2, 4, 6, 7, 9, 10), "Lydian dominant", "melodic-minor"),
  MixolydianFlat6: _fn(_scaleMask(0, 2, 4, 5, 7, 8, 10), "Mixolydian b6", "melodic-minor"),
  LocrianNatural2: _fn(_scaleMask(0, 2, 3, 5, 6, 8, 10), "Locrian natural 2", "melodic-minor"),
  Altered:         _fn(_scaleMask(0, 1, 3, 4, 6, 8, 10), "Altered (Super Locrian)", "melodic-minor"),

  // --- Harmonic minor and its modes (functional) ----------------------------
  HarmonicMinor:    _fn(_scaleMask(0, 2, 3, 5, 7, 8, 11), "Harmonic minor", "harmonic-minor"),
  LocrianNatural6:  _fn(_scaleMask(0, 1, 3, 5, 6, 9, 10), "Locrian natural 6", "harmonic-minor"),
  IonianSharp5:     _fn(_scaleMask(0, 2, 4, 5, 8, 9, 11), "Ionian #5", "harmonic-minor"),
  DorianSharp4:     _fn(_scaleMask(0, 2, 3, 6, 7, 9, 10), "Dorian #4 (Ukrainian)", "harmonic-minor"),
  PhrygianDominant: _fn(_scaleMask(0, 1, 4, 5, 7, 8, 10), "Phrygian dominant", "harmonic-minor"),
  LydianSharp2:     _fn(_scaleMask(0, 3, 4, 6, 7, 9, 11), "Lydian #2", "harmonic-minor"),
  Ultralocrian:     _fn(_scaleMask(0, 1, 3, 4, 6, 8, 9), "Ultralocrian", "harmonic-minor"),

  // --- Harmonic major and other named heptatonics (functional) --------------
  HarmonicMajor:   _fn(_scaleMask(0, 2, 4, 5, 7, 8, 11), "Harmonic major", "harmonic-major"),
  DoubleHarmonic:  _fn(_scaleMask(0, 1, 4, 5, 7, 8, 11), "Double harmonic (Byzantine)", "exotic"),
  HungarianMinor:  _fn(_scaleMask(0, 2, 3, 6, 7, 8, 11), "Hungarian minor", "exotic"),
  HungarianMajor:  _fn(_scaleMask(0, 3, 4, 6, 7, 9, 10), "Hungarian major", "exotic"),
  NeapolitanMajor: _fn(_scaleMask(0, 1, 3, 5, 7, 9, 11), "Neapolitan major", "exotic"),
  NeapolitanMinor: _fn(_scaleMask(0, 1, 3, 5, 7, 8, 11), "Neapolitan minor", "exotic"),

  // --- Pentatonic and blues (functional) ------------------------------------
  MajorPentatonic: _fn(_scaleMask(0, 2, 4, 7, 9), "Major pentatonic", "pentatonic"),
  MinorPentatonic: _fn(_scaleMask(0, 3, 5, 7, 10), "Minor pentatonic", "pentatonic"),
  Blues:           _fn(_scaleMask(0, 3, 5, 6, 7, 10), "Blues (minor)", "blues"),

  // --- Bebop (functional, 8-note; passing tone documented in SPEC) ----------
  BebopDominant: _fn(_scaleMask(0, 2, 4, 5, 7, 9, 10, 11), "Bebop dominant", "bebop"),
  BebopMajor:    _fn(_scaleMask(0, 2, 4, 5, 7, 8, 9, 11), "Bebop major", "bebop"),
  BebopDorian:   _fn(_scaleMask(0, 2, 3, 4, 5, 7, 9, 10), "Bebop Dorian", "bebop"),
  BebopMinor:    _fn(_scaleMask(0, 2, 3, 5, 7, 9, 10, 11), "Bebop minor", "bebop"),

  // --- Symmetric / atonal (NON-functional: membership only) -----------------
  WholeTone:           _sym(_scaleMask(0, 2, 4, 6, 8, 10), "Whole tone", "symmetric"),
  DiminishedHalfWhole: _sym(_scaleMask(0, 1, 3, 4, 6, 7, 9, 10), "Diminished (half-whole)", "symmetric"),
  DiminishedWholeHalf: _sym(_scaleMask(0, 2, 3, 5, 6, 8, 9, 11), "Diminished (whole-half)", "symmetric"),
  Augmented:           _sym(_scaleMask(0, 3, 4, 7, 8, 11), "Augmented", "symmetric"),
  Chromatic:           _sym(_scaleMask(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11), "Chromatic", "atonal"),
} as const;

/**
 * Return the 36-bit mask for a named scale (the descriptor's `mask` field).
 * @param name - Scale member name ("Major", "Dorian", …)
 */
export function scaleValue(name: string): bigint {
  const d = Scales[name];
  if (d === undefined) throw new Error(`Unknown scale name: ${name}`);
  return d.mask;
}

/**
 * True if `pitchClass` (0–11 semitones above the tonic) is in the scale.
 *
 * Defined for EVERY scale — the membership tier of the two-tier model —
 * including symmetric/atonal scales whose functional queries are undefined.
 * Mirrors Python `contains`.
 */
export function contains(scale: ScaleDescriptor, pitchClass: number): boolean {
  const mask = scale.mask;
  const size = Math.floor(bigintBitLength(mask) / 3); // the 12-bit copy width
  const pattern = mask >> BigInt(2 * size); // the leading 12-bit copy
  const idx = ((pitchClass % size) + size) % size;
  return Boolean((pattern >> BigInt(size - 1 - idx)) & 1n);
}
