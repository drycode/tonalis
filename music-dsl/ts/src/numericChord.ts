/**
 * numericChord.ts — NumericChord parser + serializer.
 *
 * Port of:
 *   music_dsl/domain/chords/numeric_chord.py  (NumericChord class)
 *
 * Design:
 *   - No singleton / @cache — structural, deterministic parse.
 *   - fromChordString(s) parses a numeric chord string ("V7/V", "sV7", "ii-7")
 *   - fromChord(keyRoot, chord, substitution) converts an absolute Chord to a NumericChordModel
 *   - serializeNumericChord serializes the model to the canonical JSON shape
 *
 * The substitution branches (the crux of correctness):
 *   (a) semitonesApartAscending(chord.root, keyRoot) == Tritone(6) + chord.hf==Subdominant
 *       → modulate(Tritone+M2 = 8, degree)
 *   (b) chord.harmonic_function == Dominant (and not branch-a)
 *       → modulate(Tritone = 6, degree)
 *   (c) semitonesApartAscending(chord.root, keyRoot) == m6(8)  [structural equality — NOT M3-up A==4]
 *       → modulate(m6.down()+M2 = -8+2 = -6, degree)
 */

import { type Note } from "./notes.js";
import {
  HarmonicFunction,
  Triad,
  type Triad as TriadT,
  type Seventh as SeventhT,
  type Extensions as ExtensionsT,
  type HarmonicFunction as HarmonicFunctionT,
} from "./chordQuality.js";
import {
  SCALE_DEGREES,
  type ScaleDegreeT,
} from "./scaleDegree.js";
import { semitonesApartAscending } from "./helpers.js";
import { type ChordModel, type ChordSerialized, parseChord, serializeChord, InvalidChordStringError } from "./chord.js";
import { intervalSemitones } from "./intervals.js";
import {
  sdToFlat, sdToSharp, sdToMajor, sdToMinor,
  sdIsFlat, sdIsMinor, sdNormalize, sdGetIndex,
} from "./scaleDegreeHelpers.js";

// ---------------------------------------------------------------------------
// Interval constants (semitone values used in substitution branches)
// ---------------------------------------------------------------------------

const TRITONE = intervalSemitones("Tritone");  // 6
const M2 = intervalSemitones("M2");            // 2
const M6 = intervalSemitones("M6");            // 9  (unused but documented)
const m6 = intervalSemitones("m6");            // 8
// m6.down() = -8, so m6.down() + M2 = -8 + 2 = -6
const BRANCH_C_MODULATE = -m6 + M2;           // -6

// ---------------------------------------------------------------------------
// Public error type
// ---------------------------------------------------------------------------

export class IncorrectHarmonicFunctionError extends Error {
  constructor(chord: string, keyRoot: string, hf: string) {
    super(`${chord} in the key of ${keyRoot} is not ${hf}`);
    this.name = "IncorrectHarmonicFunctionError";
  }
}

// ---------------------------------------------------------------------------
// NumericChord model (plain data — no singleton)
// ---------------------------------------------------------------------------

/** The attrs for one side (numerator or denominator) of a NumericChord. */
export interface NumericChordAttrs {
  root: ScaleDegreeT;
  triad: TriadT;
  seventh: SeventhT;
  extensions: ExtensionsT[];
  harmonic_function: HarmonicFunctionT;
  substitution: boolean;
}

/** The full NumericChord model: numerator + optional denominator. */
export interface NumericChordModel {
  numerator: NumericChordAttrs;
  denominator: NumericChordAttrs | null;
}

// ---------------------------------------------------------------------------
// Serialization shape
// ---------------------------------------------------------------------------

export interface NumericChordAttrsSerialized {
  root: string;
  triad: string;
  seventh: string;
  extensions: string[];
  harmonic_function: string;
  substitution: boolean;
}

export interface NumericChordSerialized {
  numerator: NumericChordAttrsSerialized;
  denominator: NumericChordAttrsSerialized | null;
}

// ---------------------------------------------------------------------------
// Regex (port of NumericChord.__regex__)
//
// Python: r"^(?P<root>[b#]?[ivVI]{1,4})" + AbstractChord.__regex_suffix__
// JS:  (?P<x>) → (?<x>), \d → [0-9]
// ---------------------------------------------------------------------------

const NUMERIC_REGEX = new RegExp(
  "^(?<root>[b#]?[ivVI]{1,4})" +
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
// modulate for ScaleDegree — mirrors Python transactions.modulate (ScaleDegree branch)
// ---------------------------------------------------------------------------

/**
 * Modulate a scale degree by semitones.
 * new_idx = (get_index(degree) + semitones) % 12
 * result = SCALE_DEGREES[new_idx].normalize(degree.is_flat, degree.is_minor)
 */
function modulateDegree(semitones: number, degree: ScaleDegreeT): ScaleDegreeT {
  const idx = sdGetIndex(degree);
  const newIdx = ((idx + semitones) % 12 + 12) % 12;
  const base = SCALE_DEGREES[newIdx]!;
  const isFlat = sdIsFlat(degree);
  const isMinor = sdIsMinor(degree);
  return sdNormalize(base, isFlat, isMinor);
}

// ---------------------------------------------------------------------------
// mOrMScaleDegree — mirror of Python m_or_M_scaledegree
// Major-third triads (Major, Augmented, Sus4) keep the major degree;
// everything else (Minor, Dim, HalfDim, Sus, Sus2) lowers it.
// ---------------------------------------------------------------------------

function mOrMScaleDegree(degree: ScaleDegreeT, triad: TriadT): ScaleDegreeT {
  if (triad && triad !== Triad.Augmented && triad !== Triad.Sus4) {
    return sdToMinor(degree) as ScaleDegreeT;
  }
  return degree;
}

// ---------------------------------------------------------------------------
// findScaleDegree — mirror of Python NumericChord._find_scale_degree
// ---------------------------------------------------------------------------

function findScaleDegree(keyRoot: string, chordRoot: string, triad: TriadT): ScaleDegreeT {
  const semitones = semitonesApartAscending(keyRoot, chordRoot);
  let degree = SCALE_DEGREES[semitones]!;
  // Diminished chords are conventionally spelled with a sharp on a chromatic degree
  if (triad === Triad.Diminished && sdIsFlat(degree)) {
    degree = sdToSharp(degree);
  }
  return mOrMScaleDegree(degree, triad);
}

// ---------------------------------------------------------------------------
// getHarmonicFunction — mirror of AbstractChord._get_harmonic_function
// ---------------------------------------------------------------------------

function getHarmonicFunction(triad: TriadT, seventh: SeventhT): HarmonicFunctionT {
  const key = `${triad}__${seventh}`;
  const table: Record<string, HarmonicFunctionT> = {
    [`${Triad.Minor}__7`]:          HarmonicFunction.Subdominant,
    [`${Triad.HalfDiminished}__7`]: HarmonicFunction.Subdominant,
    [`${Triad.Major}__7`]:          HarmonicFunction.Dominant,
    [`${Triad.Major}__^7`]:         HarmonicFunction.Tonic,
    [`${Triad.Minor}__^7`]:         HarmonicFunction.Tonic,
  };
  return table[key] ?? HarmonicFunction.Tonic;
}

// ---------------------------------------------------------------------------
// Seventh normalization (shared with chord.ts logic)
// ---------------------------------------------------------------------------

function normalizeSeventh(token: string | undefined): SeventhT {
  if (!token) return "" as SeventhT;
  if (token === "^") return "^7" as SeventhT;
  return token as SeventhT;
}

// ---------------------------------------------------------------------------
// Extension parsing (mirrors AbstractChord._get_extensions)
// ---------------------------------------------------------------------------

// Known valid extension values (mirrors Python Extensions enum)
const VALID_EXTENSIONS: ReadonlySet<string> = new Set(Object.values({
  _None: "",
  add2: "2", add3: "3", b5: "b5", add5: "5", s5: "#5", b6: "b6",
  add6: "6", b9: "b9", add9: "9", s9: "#9", add11: "11", s11: "#11",
  b13: "b13", add13: "13", alt: "alt",
}).filter(v => v !== ""));

function getExtensions(extToken: string): ExtensionsT[] {
  if (!extToken) return [];
  let s = extToken.replace(/add/g, "");
  s = s.replace(/69/g, "6,9");
  const EXT_RE = /[b#]?[0-9]{1,2}/g;
  const results: ExtensionsT[] = [];
  let pos = 0;
  while (pos < s.length) {
    EXT_RE.lastIndex = 0;
    const sub = s.slice(pos);
    const m = EXT_RE.exec(sub);
    if (m === null || m.index !== 0) {
      pos += 1;
      continue;
    }
    const token = m[0];
    if (!VALID_EXTENSIONS.has(token)) {
      throw new InvalidChordStringError(`Unknown extension token: ${token}`);
    }
    results.push(token as ExtensionsT);
    pos += token.length;
  }
  return results;
}

// ---------------------------------------------------------------------------
// parseNumericRoot — mirror of Python NumericChord._parse_root
// Parses the roman numeral root from the regex match (the root IS a ScaleDegree value).
// ---------------------------------------------------------------------------

function parseNumericRoot(match: string): ScaleDegreeT {
  // The root match is already in ScaleDegree value form (e.g. "V", "bVI", "#iv")
  // Normalize: Python ScaleDegree(match) — just use the value directly
  return match as ScaleDegreeT;
}

// ---------------------------------------------------------------------------
// parseNumericString — parse one side of a numeric chord string (no "/" handling)
// ---------------------------------------------------------------------------

function parseNumericString(s: string, substitution: boolean): NumericChordAttrs {
  if (!s) {
    throw new InvalidChordStringError(
      "Attempted to parse a numeric chord with an empty numerator"
    );
  }

  const match = NUMERIC_REGEX.exec(s);
  if (!match || !match.groups) {
    throw new InvalidChordStringError(
      `Attempted to parse numeric chord "${s}" which is invalid`
    );
  }
  const g = match.groups;
  const rawRoot = parseNumericRoot(g["root"]!);

  // Collect sus
  let _sus: string | undefined = g["sus1"] || g["sus2"] || undefined;
  if (g["sus_short"]) {
    _sus = _sus || "sus4";
  }

  const triadToken: string | undefined = g["triad"] || undefined;
  const triadIsSus = triadToken === "sus" || triadToken === "sus4" || triadToken === "sus2";

  if (_sus && triadToken && !triadIsSus) {
    throw new InvalidChordStringError(
      `Attempted to parse "${s}": a triad and a sus cannot coexist (${triadToken} + ${_sus})`
    );
  }

  const triadStr = _sus || triadToken || "";
  const triad = triadStr as TriadT;

  // Mirror Python make_chord_attrs → m_or_M_scaledegree: lower the root case for minor-quality triads.
  const root = mOrMScaleDegree(rawRoot, triad);

  const seventh = normalizeSeventh(g["seventh"]);
  const extToken = g["ext"] || "";

  let extensions: ExtensionsT[];
  let resolvedSeventh = seventh;
  if (g["alt"]) {
    if (triad === "sus" || triad === "sus2" || triad === "sus4") {
      throw new InvalidChordStringError(
        `Attempted to parse "${s}": "alt" cannot modify a sus chord`
      );
    }
    resolvedSeventh = "7" as SeventhT;
    extensions = ["alt" as ExtensionsT, ...getExtensions(extToken)];
  } else {
    extensions = getExtensions(extToken);
  }

  if (g["aug5"] && !extensions.includes("#5" as ExtensionsT)) {
    extensions = [...extensions, "#5" as ExtensionsT];
  }

  const harmFunc = getHarmonicFunction(triad, resolvedSeventh);

  return {
    root,
    triad,
    seventh: resolvedSeventh,
    extensions,
    harmonic_function: harmFunc,
    substitution,
  };
}

// ---------------------------------------------------------------------------
// fromChordString — public: parse a numeric chord string into a NumericChordModel
// ---------------------------------------------------------------------------

/**
 * Parse a numeric chord string ("V7", "V7/V", "ii-7", "sV7") into a NumericChordModel.
 * Mirrors Python NumericChord.from_chord_string + _make_new.
 *
 * Leading "s" on the numerator → substitution=true.
 * "/" splits numerator from denominator.
 */
export function fromChordString(s: string): NumericChordModel {
  if (!s) {
    throw new InvalidChordStringError(
      "Attempted to parse a numeric chord with an empty numerator"
    );
  }

  const parts = s.split("/");
  let numeratorStr = parts[0];
  const denominatorStr = parts.length === 2 ? parts[1] : null;

  if (!numeratorStr) {
    throw new InvalidChordStringError(
      "Attempted to parse a numeric chord with an empty numerator"
    );
  }

  // Leading "s" → substitution=true
  let substitution = false;
  if (numeratorStr[0] === "s") {
    substitution = true;
    numeratorStr = numeratorStr.slice(1);
  }

  const numerator = parseNumericString(numeratorStr, substitution);

  let denominator: NumericChordAttrs | null = null;
  if (denominatorStr) {
    // Denominator is parsed recursively (no substitution flag)
    const denModel = fromChordString(denominatorStr);
    denominator = denModel.numerator;
  }

  return { numerator, denominator };
}

// ---------------------------------------------------------------------------
// fromChord — convert an absolute Chord to NumericChordAttrs given a key root
// ---------------------------------------------------------------------------

/**
 * Convert an absolute Chord to a NumericChordAttrs in a given key.
 * Mirrors Python NumericChord._from_chord(diatonic_key_root, chord, substitution).
 *
 * The three substitution branches:
 *   (a) semitonesApartAscending(chord.root, keyRoot) == Tritone(6) AND hf==Subdominant
 *       → require Subdominant else throw IncorrectHarmonicFunctionError
 *       → modulate(Tritone+M2 = 8, degree)
 *   (b) chord.harmonic_function == Dominant (checked after branch-a fails)
 *       → modulate(Tritone = 6, degree)
 *   (c) semitonesApartAscending(chord.root, keyRoot) == m6(8)
 *       → modulate(m6.down()+M2 = -6, degree)
 *       NOTE: A==8 fires; A==4 (M3-up inversion) does NOT (structural equality).
 */
export function fromChord(
  keyRoot: string,
  chord: ChordModel,
  substitution: boolean,
): NumericChordAttrs {
  let scaleDegree = findScaleDegree(keyRoot, chord.root, chord.triad);

  if (substitution) {
    const A = semitonesApartAscending(chord.root, keyRoot);

    if (A === TRITONE) {
      // Branch (a): tritone root motion + must be Subdominant
      if (chord.harmonic_function !== HarmonicFunction.Subdominant) {
        throw new IncorrectHarmonicFunctionError(
          chord.root,
          keyRoot,
          HarmonicFunction.Subdominant,
        );
      }
      scaleDegree = modulateDegree(TRITONE + M2, scaleDegree);
    } else if (chord.harmonic_function === HarmonicFunction.Dominant) {
      // Branch (b): dominant quality chord
      scaleDegree = modulateDegree(TRITONE, scaleDegree);
    } else if (A === m6) {
      // Branch (c): m6 ascending root motion (A==8 only, NOT M3-up A==4)
      scaleDegree = modulateDegree(BRANCH_C_MODULATE, scaleDegree);
    }
  }

  const harmFunc = getHarmonicFunction(chord.triad, chord.seventh);

  return {
    root: scaleDegree,
    triad: chord.triad,
    seventh: chord.seventh,
    extensions: chord.extensions.slice(),
    harmonic_function: harmFunc,
    substitution,
  };
}

// ---------------------------------------------------------------------------
// serializeNumericChord — canonical JSON serializer
// ---------------------------------------------------------------------------

/**
 * Serialize a NumericChordModel to the canonical JSON shape.
 * Shape: { numerator: <chord-model with ScaleDegree root>, denominator: <same>|null }
 * Root is a ScaleDegree value string (not a Notes value).
 * No bass, no encoding.
 */
export function serializeNumericChord(model: NumericChordModel): NumericChordSerialized {
  function serializeAttrs(attrs: NumericChordAttrs): NumericChordAttrsSerialized {
    return {
      root: attrs.root,
      triad: attrs.triad,
      seventh: attrs.seventh,
      extensions: attrs.extensions.slice(),
      harmonic_function: attrs.harmonic_function,
      substitution: attrs.substitution,
    };
  }

  return {
    numerator: serializeAttrs(model.numerator),
    denominator: model.denominator ? serializeAttrs(model.denominator) : null,
  };
}

// ---------------------------------------------------------------------------
// Resolution-set constants (port of static/__init__.py)
// These are analysis-layer; no conformance op consumes them directly.
// Values mirror Python: Intervals.X.up() = +X, Intervals.X.down() = -X
// ---------------------------------------------------------------------------

export const SUBSTITUTE_RESOLUTIONS: ReadonlySet<number> = new Set([
  -intervalSemitones("m2"),  // m2.down() = -1
  intervalSemitones("M7"),   // M7.up()   = 11
]);

export const DOMINANT_RESOLUTIONS: ReadonlySet<number> = new Set([
  ...SUBSTITUTE_RESOLUTIONS,
  intervalSemitones("P5"),   // P5.up()   = 7
  intervalSemitones("P4"),   // P4.up()   = 5
  intervalSemitones("M2"),   // M2.up()   = 2
  -intervalSemitones("m7"),  // m7.down() = -10
]);

// SUBDOMINANT = (SUBSTITUTE ^ DOMINANT) ^ {M2.up(), M7.up()}
// = symmetric difference of SUBSTITUTE and DOMINANT, then XOR {2, 11}
function xorSets<T>(...sets: ReadonlySet<T>[]): Set<T> {
  let result = new Set<T>();
  for (const s of sets) {
    for (const v of s) {
      if (result.has(v)) result.delete(v);
      else result.add(v);
    }
  }
  return result;
}

export const SUBDOMINANT_RESOLUTIONS: ReadonlySet<number> = xorSets(
  SUBSTITUTE_RESOLUTIONS,
  DOMINANT_RESOLUTIONS,
  new Set([intervalSemitones("M2"), intervalSemitones("M7")]),
);

export const MAJOR_HARMONIC_FUNCTIONS = {
  tonic: new Set([
    intervalSemitones("M3"),    // M3.up()   = 4
    -intervalSemitones("m6"),   // m6.down() = -8
    intervalSemitones("M6"),    // M6.up()   = 9
    -intervalSemitones("m3"),   // m3.down() = -3
  ]),
  dominant: new Set([
    intervalSemitones("M7"),    // M7.up()   = 11
    -intervalSemitones("m2"),   // m2.down() = -1
    intervalSemitones("P5"),    // P5.up()   = 7
    -intervalSemitones("P4"),   // P4.down() = -5
  ]),
  subdominant: new Set([
    intervalSemitones("M2"),    // M2.up()   = 2
    -intervalSemitones("m7"),   // m7.down() = -10
    intervalSemitones("P4"),    // P4.up()   = 5
    -intervalSemitones("P5"),   // P5.down() = -7
  ]),
} as const;
