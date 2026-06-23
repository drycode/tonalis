/**
 * chord.ts — absolute Chord parser + serializer (port of AbstractChord / Chord).
 *
 * Port of:
 *   music_dsl/domain/chords/abstract_chord.py  (parser logic, harmonic function table)
 *   music_dsl/domain/chords/chord.py            (_parse_root, Chord class)
 *
 * Deviations from the Python reference (all intentional per shared-context):
 *   - No singleton / @cache — structural, deterministic parse.
 *   - One typed InvalidChordStringError (not Exception subclass).
 *   - Named-group syntax: (?<x>) instead of (?P<x>).
 *   - \d → [0-9] (ASCII-only digit contract).
 *   - Returns plain objects, not ChordAttrs dataclass.
 */

import { type Note, noteToFlat } from "./notes.js";
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
import { encodingValue } from "./encode.js";

// ---------------------------------------------------------------------------
// Public error type
// ---------------------------------------------------------------------------

export class InvalidChordStringError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InvalidChordStringError";
  }
}

// ---------------------------------------------------------------------------
// Parsed chord model (structural, no singleton)
// ---------------------------------------------------------------------------

export interface ChordModel {
  root: Note;
  triad: TriadT;
  seventh: SeventhT;
  extensions: ExtensionsT[];
  harmonic_function: HarmonicFunctionT;
  substitution: boolean;
}

// ---------------------------------------------------------------------------
// Serialized chord shape (the canonical JSON model)
// ---------------------------------------------------------------------------

export interface ChordSerialized {
  root: string;
  triad: string;
  seventh: string;
  extensions: string[];
  harmonic_function: string;
  substitution: boolean;
}

// ---------------------------------------------------------------------------
// Regex (ported from AbstractChord.__regex__ + __regex_suffix__)
//
// Python reference (verbatim):
//   r"(?P<sus_short>4)?"
//   r"(?P<triad>sus4|sus2|sus|[ho+\-])?"
//   r"(?P<seventh>\^7|\^|7)?"
//   r"(?P<aug5>\+)?"
//   r"(?P<alt>alt)?"
//   r"(?P<sus1>sus4|sus2|sus)?"
//   r"(?P<ext>(?:add|[b#]?\d{1,2})*?)"
//   r"(?P<sus2>sus4|sus2|sus)?"
//   r"$"
//
// JS adjustments: (?P<x>) → (?<x>), \d → [0-9]
// ---------------------------------------------------------------------------

const CHORD_REGEX = new RegExp(
  "^(?<root>[A-G][b#]?)" +
  "(?<sus_short>4)?" +
  "(?<triad>sus4|sus2|sus|[ho+\\-])?" +
  "(?<seventh>\\^7|\\^|7)?" +
  "(?<aug5>\\+)?" +
  "(?<alt>alt)?" +
  "(?<sus1>sus4|sus2|sus)?" +
  "(?<ext>(?:add|[b#]?[0-9]{1,2})*?)" +
  "(?<sus2>sus4|sus2|sus)?" +
  "$"
);

// ---------------------------------------------------------------------------
// Enharmonic root map (Chord._ENHARMONIC_ROOTS)
// ---------------------------------------------------------------------------

const ENHARMONIC_ROOTS: Readonly<Record<string, string>> = {
  Cb: "B",
  Fb: "E",
  "B#": "C",
  "E#": "F",
};

// ---------------------------------------------------------------------------
// Reverse-lookup maps: value → member name (for encodingValue call)
// ---------------------------------------------------------------------------

function triadNameFromValue(value: TriadT): string {
  for (const [k, v] of Object.entries(Triad)) {
    if (v === value) return k;
  }
  throw new InvalidChordStringError(`Unknown Triad value: ${value}`);
}

function seventhNameFromValue(value: SeventhT): string {
  for (const [k, v] of Object.entries(Seventh)) {
    if (v === value) return k;
  }
  throw new InvalidChordStringError(`Unknown Seventh value: ${value}`);
}

function extensionNameFromValue(value: ExtensionsT): string {
  for (const [k, v] of Object.entries(Extensions)) {
    if (v === value) return k;
  }
  throw new InvalidChordStringError(`Unknown Extensions value: ${value}`);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Mirror of _normalize_seventh: "^" → "^7", else value or "". */
function normalizeSeventh(token: string | undefined): SeventhT {
  if (!token) return Seventh._None;
  if (token === "^") return Seventh.Major; // "^7"
  const v = token as SeventhT;
  // Validate it's a real Seventh value
  if (!Object.values(Seventh).includes(v)) {
    throw new InvalidChordStringError(`Unknown seventh token: ${token}`);
  }
  return v;
}

/** Mirror of _get_extensions. */
function getExtensions(extString: string): ExtensionsT[] {
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

/** Mirror of _get_harmonic_function. */
function getHarmonicFunction(triad: TriadT, seventh: SeventhT): HarmonicFunctionT {
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

/** Mirror of _parse_root: apply enharmonic map then flat-normalize. */
function parseRoot(match: string): Note {
  const mapped = ENHARMONIC_ROOTS[match] ?? match;
  return noteToFlat(mapped) as Note;
}

/**
 * make_chord_attrs rejection rule (ported from abstract_chord.py):
 * Notes root + Triad.Major + Seventh._None + 1-char root value
 * + extensions present + leading b/# extension → throw.
 */
function checkMakeChordAttrsRejection(
  root: Note,
  triad: TriadT,
  seventh: SeventhT,
  extensions: ExtensionsT[],
): void {
  if (
    triad === Triad.Major &&
    seventh === Seventh._None &&
    root.length === 1 &&
    extensions.length > 0 &&
    (extensions[0][0] === "b" || extensions[0][0] === "#")
  ) {
    throw new InvalidChordStringError(
      `${root}${extensions[0]}: an altered tension with no seventh ` +
      "binds its accidental to the root and has no spellable canonical form"
    );
  }
}

// ---------------------------------------------------------------------------
// Core parse implementation (mirrors _parse_chord_string_impl)
// ---------------------------------------------------------------------------

function parseChordStringImpl(rawChord: string): ChordModel {
  // Bass split: discard bass note
  let s = rawChord;
  if (s.includes("/")) {
    s = s.split("/")[0];
  }

  // Pipe check
  if (rawChord.includes("|")) {
    throw new InvalidChordStringError(
      "There's more than one chord in this attempt to parse"
    );
  }

  const match = CHORD_REGEX.exec(s);
  if (!match || !match.groups) {
    throw new InvalidChordStringError(
      `Attempted to parse "${rawChord}" which is invalid`
    );
  }

  const g = match.groups;
  const root = parseRoot(g["root"]);

  // Collect sus from sus1/sus2 positions
  let _sus: string | undefined = g["sus1"] || g["sus2"] || undefined;
  if (g["sus_short"]) {
    // bare "4" → sus4 if no other sus collected
    _sus = _sus || "sus4";
  }

  const triadToken: string | undefined = g["triad"] || undefined;
  const triadIsSus = triadToken === "sus" || triadToken === "sus4" || triadToken === "sus2";

  // Reject: triad + sus coexist (and triad is not itself a sus type)
  if (_sus && triadToken && !triadIsSus) {
    throw new InvalidChordStringError(
      `Attempted to parse "${rawChord}": a triad and a sus cannot coexist (${triadToken} + ${_sus})`
    );
  }

  const triadStr = _sus || triadToken || "";
  const triad = triadStr as TriadT;
  // Validate triad value
  if (!Object.values(Triad).includes(triad)) {
    throw new InvalidChordStringError(`Unknown triad value: ${triadStr}`);
  }

  const seventh = normalizeSeventh(g["seventh"]);
  const extToken = g["ext"] || "";

  let extensions: ExtensionsT[];
  let resolvedSeventh = seventh;
  if (g["alt"]) {
    // alt on sus → reject
    if (triad === Triad.Sus || triad === Triad.Sus2 || triad === Triad.Sus4) {
      throw new InvalidChordStringError(
        `Attempted to parse "${rawChord}": "alt" cannot modify a sus chord`
      );
    }
    // alt forces minor seventh; alt goes first in extensions
    resolvedSeventh = Seventh.Minor;
    extensions = [Extensions.alt, ...getExtensions(extToken)];
  } else {
    extensions = getExtensions(extToken);
  }

  // aug5: "+" after seventh → append "#5" if not already present
  // This runs for BOTH the alt and non-alt paths (mirrors Python reference behaviour).
  if (g["aug5"] && !extensions.includes(Extensions.s5)) {
    extensions = [...extensions, Extensions.s5];
  }

  const harmFunc = getHarmonicFunction(triad, resolvedSeventh);
  checkMakeChordAttrsRejection(root, triad, resolvedSeventh, extensions);

  return { root, triad, seventh: resolvedSeventh, extensions, harmonic_function: harmFunc, substitution: false };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Parse a chord string into a ChordModel.
 * Throws InvalidChordStringError for any invalid input.
 * Mirrors AbstractChord._parse_chord_string (robustness funnel).
 */
export function parseChord(rawChord: string): ChordModel {
  try {
    return parseChordStringImpl(rawChord);
  } catch (err) {
    if (err instanceof InvalidChordStringError) throw err;
    // Funnel: any lower-level error → typed error
    const msg = err instanceof Error ? `${err.constructor.name}: ${err.message}` : String(err);
    throw new InvalidChordStringError(
      `Attempted to parse "${rawChord}" which is invalid (${msg})`
    );
  }
}

/**
 * Serialize a ChordModel to the canonical JSON shape.
 * The shape is the contract (byte-identical to the Python reference serializer).
 */
export function serializeChord(chord: ChordModel): ChordSerialized {
  return {
    root: chord.root,
    triad: chord.triad,
    seventh: chord.seventh,
    extensions: chord.extensions.slice(),
    harmonic_function: chord.harmonic_function,
    substitution: chord.substitution,
  };
}

/**
 * Compute the encoding value for a chord string.
 * Parses the chord then delegates to encodingValue (from Build 2).
 * Throws InvalidChordStringError for invalid input.
 */
export function chordEncoding(rawChord: string): bigint {
  const chord = parseChord(rawChord); // throws on invalid
  const triadName = triadNameFromValue(chord.triad);
  const seventhName = seventhNameFromValue(chord.seventh);
  const extNames = chord.extensions.map(extensionNameFromValue);
  return encodingValue(triadName, seventhName, extNames);
}
