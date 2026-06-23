/**
 * encode — chord encoding + scale bit-vectors.
 * Port of music_dsl/encode.py using BigInt (Scales are 36-bit; JS << truncates at 32 bits).
 *
 * The Python reference keyed EncodingMap by enum TYPE (Triad.Minor ≠ Seventh.Minor).
 * Here we maintain three separate lookup maps by role (triad / seventh / extension)
 * so name collisions ("Minor" means [3,7] for a Triad but [10] for a Seventh) are
 * resolved by context, matching the Python reference exactly.
 */

/** Sentinel / root bit at position 18 (bit 18 of the 19-bit chord encoding). */
export const EMPTY_CHORD_ENCODING: bigint = 1n << 18n; // 262144n

/** Bit-length of the chord encoding vector (19 bits). */
const CHORD_ENCODING_BIT_LENGTH = 19;

/** Special-cased fully-diminished core encoding. */
export const DIMINISHED_ENCODING: bigint = BigInt(0b1001001001000000000); // 299520n

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

/**
 * ENCODING_MAP — the unified flat map (keyed by enum VALUE, as in the Python
 * reference).  Exposed for consumers that already resolved enum type.
 * Note: collisions are expected ("Minor" = Triad value "-" vs. Seventh value "7");
 * callers that need role-disambiguation use TRIAD_MAP / SEVENTH_MAP / EXTENSION_MAP.
 */
export const ENCODING_MAP: Readonly<Record<string, readonly number[]>> = {
  ...TRIAD_MAP,
  ...SEVENTH_MAP,
  ...EXTENSION_MAP,
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

/**
 * Scale bit-vectors (36-bit, pattern repeated ×3 for modal alignment).
 * Mirrors Scales enum in encode.py.
 */
export const Scales: Readonly<Record<string, bigint>> = {
  Major:         BigInt(parseInt("101011010101".repeat(3), 2)),
  Minor:         BigInt(parseInt("101101011010".repeat(3), 2)),
  HarmonicMinor: BigInt(parseInt("101101011001".repeat(3), 2)),
} as const;

/**
 * Return the bigint value for a named scale.
 * @param name - Scale member name ("Major", "Minor", "HarmonicMinor")
 */
export function scaleValue(name: string): bigint {
  const v = Scales[name];
  if (v === undefined) throw new Error(`Unknown scale name: ${name}`);
  return v;
}
