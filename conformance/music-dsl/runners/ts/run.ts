/**
 * music-dsl TypeScript conformance runner (vitest suite). Discovers every
 * conformance/music-dsl/cases/ ** /*.json and dispatches each case's `op` against the music_dsl
 * TS port, asserting `expect.value`. The op set IS the cross-port contract (mirrors the Python
 * runner's OPS). Lookup-mode per the contract: Intervals by member NAME, Notes/ScaleDegree by VALUE.
 */
import { describe, it, expect } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";

import {
  intervalsEqual, intervalSemitones, notesEqual, noteIndex, scaleDegreesEqual,
  scaleValue, encodingValue, stripLeft, stripRight, semitonesApartAscending,
  parseChord, serializeChord, chordEncoding,
  fromChordString, fromChord, serializeNumericChord,
  modulate, isDiatonic, harmonicFunctionInKey, chordInKey,
  IncorrectHarmonicFunctionError, InvalidChordStringError,
} from "music_dsl";

const HERE = dirname(fileURLToPath(import.meta.url));
const CASES_DIR = join(HERE, "..", "..", "cases");

type Case = { name: string; op: string; args: Record<string, unknown>; expect: { value?: unknown; model?: unknown; error?: boolean } };

// The op dispatch — the cross-port contract. Same op names as Python/Rust runners.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const OPS: Record<string, (args: any) => unknown> = {
  intervals_equal:           (a) => intervalsEqual(a["a"] as string, a["b"] as string),
  interval_semitones:        (a) => intervalSemitones(a["x"] as string),
  notes_equal:               (a) => notesEqual(a["a"] as string, a["b"] as string),
  note_index:                (a) => noteIndex(a["n"] as string),
  scale_degrees_equal:       (a) => scaleDegreesEqual(a["a"] as string, a["b"] as string),
  // Encode / helpers ops (Build 2) — bigint layer; convert to number for JSON comparison
  scale_value:               (a) => Number(scaleValue(a["name"] as string)),
  encoding_value:            (a) => Number(encodingValue(a["triad"] as string, a["seventh"] as string, (a["extensions"] as string[]) ?? [])),
  strip_left:                (a) => Number(stripLeft(BigInt(a["bits"] as number), Number(a["x"]))),
  strip_right:               (a) => Number(stripRight(BigInt(a["bits"] as number), Number(a["x"]))),
  semitones_apart_ascending: (a) => semitonesApartAscending(a["root"] as string, a["note"] as string),
  parse_chord:               (a) => ({ chord: serializeChord(parseChord(a["input"] as string)) }),
  encode_chord:              (a) => Number(chordEncoding(a["input"] as string)),
  // Build 4 ops: numeric_chord + transactions
  parse_numeric:             (a) => ({ numeric: serializeNumericChord(fromChordString(a["input"] as string)) }),
  numeric_from_chord:        (a) => {
    const chord = parseChord(a["chord"] as string);
    const attrs = fromChord(a["key_root"] as string, chord, a["substitution"] as boolean);
    return { numeric: serializeNumericChord({ numerator: attrs, denominator: null }).numerator };
  },
  modulate:                  (a) => modulate(a["semitones"] as number, a["note"] as string),
  is_diatonic:               (a) => isDiatonic(a["root"] as string, a["scale"] as string, parseChord(a["chord"] as string)),
  harmonic_function_in_key:  (a) => harmonicFunctionInKey(a["key_root"] as string, a["key_is_minor"] as boolean, parseChord(a["chord"] as string)),
  chord_in_key:              (a) => ({ chord: chordInKey(a["numeric"] as string, a["key_root"] as string) }),
};

function discover(dir: string): Array<{ relpath: string; case: Case }> {
  const out: Array<{ relpath: string; case: Case }> = [];
  const walk = (d: string): void => {
    for (const entry of readdirSync(d).sort()) {
      const full = join(d, entry);
      if (statSync(full).isDirectory()) walk(full);
      else if (entry.endsWith(".json")) {
        for (const c of JSON.parse(readFileSync(full, "utf-8")) as Case[]) {
          out.push({ relpath: relative(CASES_DIR, full), case: c });
        }
      }
    }
  };
  walk(dir);
  return out;
}

const EXPECTED_CASE_COUNT = 273; // keep in sync with the Python runner's frozen count

const cases = discover(CASES_DIR);

describe("music-dsl conformance suite (TypeScript port)", () => {
  it("case count is frozen", () => {
    expect(cases.length).toBe(EXPECTED_CASE_COUNT);
  });
  for (const { relpath, case: c } of cases) {
    it(`${c.name} (${relpath})`, () => {
      const op = OPS[c.op];
      if (!op) throw new Error(`unknown op ${c.op} in ${c.name}`);
      if (c.expect.error === true) {
        expect(() => op(c.args)).toThrow();
      } else if (c.expect.model !== undefined) {
        expect(op(c.args)).toEqual(c.expect.model);
      } else {
        expect(op(c.args)).toEqual(c.expect.value);
      }
    });
  }
});
