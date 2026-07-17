/**
 * chordHelpers.ts — shared chord-quality parsing primitives.
 *
 * chord.ts and numericChord.ts each carried a divergent copy of the same three
 * routines (harmonic-function table, seventh normalization, extension tokenizer).
 * This is the single source of truth; both parsers consume it.
 *
 * `InvalidChordStringError` also lives here so the helpers can throw it without a
 * chord.ts ⇄ chordHelpers circular import. chord.ts re-exports it, so its public
 * surface (`import { InvalidChordStringError } from "./chord.js"`) is unchanged.
 */

import {
  HarmonicFunction,
  Triad,
  Seventh,
  Extensions,
  type Triad as TriadT,
  type Seventh as SeventhT,
  type Extensions as ExtensionsT,
  type HarmonicFunction as HarmonicFunctionT,
} from "./chordQuality.js";

// ---------------------------------------------------------------------------
// Public error type
// ---------------------------------------------------------------------------

/** Raised for any un-parseable / invalid chord string (absolute or numeric). */
export class InvalidChordStringError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InvalidChordStringError";
  }
}

// ---------------------------------------------------------------------------
// Shared parsing primitives (mirror the Python AbstractChord helpers)
// ---------------------------------------------------------------------------

/** Mirror of _normalize_seventh: "^" → "^7", else the value or "" (validated). */
export function normalizeSeventh(token: string | undefined): SeventhT {
  if (!token) return Seventh._None;
  if (token === "^") return Seventh.Major; // "^7"
  const v = token as SeventhT;
  // Validate it's a real Seventh value
  if (!Object.values(Seventh).includes(v)) {
    throw new InvalidChordStringError(`Unknown seventh token: ${token}`);
  }
  return v;
}

/**
 * Mirror of _get_extensions.
 * Valid tokens are the non-empty members of the `Extensions` enum, so this stays
 * in lock-step with chordQuality.ts (no hand-maintained inline copy to drift).
 */
export function getExtensions(extString: string): ExtensionsT[] {
  if (!extString) return [];
  // Normalize: strip "add" prefixes, expand "69" → "6,9"
  let s = extString.replace(/add/g, "");
  s = s.replace(/69/g, "6,9");

  const EXT_TOKEN_RE = /[b#]?[0-9]{1,2}/g;
  const results: ExtensionsT[] = [];
  let pos = 0;
  while (pos < s.length) {
    // Reset lastIndex to pos and try to match at pos
    EXT_TOKEN_RE.lastIndex = 0;
    const sub = s.slice(pos);
    const m = EXT_TOKEN_RE.exec(sub);
    if (m === null || m.index !== 0) {
      // Skip a separator char (comma, unexpected char)
      pos += 1;
      continue;
    }
    const token = m[0];
    // Validate the token is a known Extensions value
    const val = token as ExtensionsT;
    if (!Object.values(Extensions).includes(val)) {
      throw new InvalidChordStringError(`Unknown extension token: ${token}`);
    }
    results.push(val);
    pos += token.length;
  }
  return results;
}

/** Mirror of _get_harmonic_function: (triad, seventh) → HarmonicFunction, default Tonic. */
export function getHarmonicFunction(triad: TriadT, seventh: SeventhT): HarmonicFunctionT {
  const key = `${triad}__${seventh}`;
  const table: Record<string, HarmonicFunctionT> = {
    [`${Triad.Minor}__${Seventh.Minor}`]:          HarmonicFunction.Subdominant,
    [`${Triad.HalfDiminished}__${Seventh.Minor}`]: HarmonicFunction.Subdominant,
    [`${Triad.Major}__${Seventh.Minor}`]:          HarmonicFunction.Dominant,
    [`${Triad.Major}__${Seventh.Major}`]:          HarmonicFunction.Tonic,
    [`${Triad.Minor}__${Seventh.Major}`]:          HarmonicFunction.Tonic,
  };
  return table[key] ?? HarmonicFunction.Tonic;
}
