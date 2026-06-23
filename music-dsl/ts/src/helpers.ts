/**
 * helpers — bit primitives for the encode/scale layer.
 * Port of music_dsl/helpers.py (strip_left, strip_right, MIN_SUPPORTED, MAX_SUPPORTED).
 * All values are BigInt; JS bitwise operators coerce to 32-bit signed and cannot
 * handle 36–39-bit Scales constants.
 */

import { noteIndex } from "./notes.js";

/** Minimum supported bit-array value (2^12 = 13-bit sentinel). */
export const MIN_SUPPORTED: bigint = BigInt(0b1000000000000); // 4096

/** Maximum supported bit-array value (39-bit, "1111111111111" × 3). */
export const MAX_SUPPORTED: bigint = BigInt(
  parseInt("1111111111111".repeat(3), 2),
);

/** bigint bit-length: position of the most-significant 1-bit. */
function bigintBitLength(n: bigint): number {
  if (n === 0n) return 0;
  let len = 0;
  let v = n;
  while (v > 0n) {
    v >>= 1n;
    len++;
  }
  return len;
}

/**
 * Remove `x` high bits from a bit-array.
 * Throws on: x==0 pass-through (ok), out-of-range `bits`, too-large shift, fidelity loss.
 * Port of helpers.py:strip_left.
 */
export function stripLeft(bits: bigint, x: number): bigint {
  if (x === 0) return bits;
  if (bits < MIN_SUPPORTED || bits > MAX_SUPPORTED) {
    throw new Error("Unexpected behavior");
  }
  const bitLen = bigintBitLength(bits);
  if (bitLen < x) {
    throw new Error("Attempting an invalid shift");
  }
  const mask = (1n << BigInt(bitLen - x)) - 1n;
  const result = bits & mask;
  if (bigintBitLength(result) !== bitLen - x) {
    throw new Error(
      "Stripping left will reduce the fidelity of the bit array, because of leading zeros after the strip",
    );
  }
  return result;
}

/**
 * Remove `x` low bits from a bit-array (right-shift).
 * Throws if `x` exceeds the bit-length of `bits`.
 * Port of helpers.py:strip_right.
 */
export function stripRight(bits: bigint, x: number): bigint {
  if (x > bigintBitLength(bits)) {
    throw new Error("Attempting an invalid shift");
  }
  return bits >> BigInt(x);
}

/**
 * Ascending semitone distance from `root` to `note` (0–11, wraps mod 12).
 * Port of helpers.py:semitones_apart_ascending.
 */
export function semitonesApartAscending(root: string, note: string): number {
  return (noteIndex(note) + 12 - noteIndex(root)) % 12;
}
