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
} from "music_dsl";

const HERE = dirname(fileURLToPath(import.meta.url));
const CASES_DIR = join(HERE, "..", "..", "cases");

type Case = { name: string; op: string; args: Record<string, string>; expect: { value?: unknown } };

// The op dispatch — the cross-port contract. Same op names as Python/Rust runners.
const OPS: Record<string, (args: Record<string, string>) => unknown> = {
  intervals_equal: (a) => intervalsEqual(a["a"]!, a["b"]!),
  interval_semitones: (a) => intervalSemitones(a["x"]!),
  notes_equal: (a) => notesEqual(a["a"]!, a["b"]!),
  note_index: (a) => noteIndex(a["n"]!),
  scale_degrees_equal: (a) => scaleDegreesEqual(a["a"]!, a["b"]!),
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

const EXPECTED_CASE_COUNT = 51; // keep in sync with the Python runner's frozen count

const cases = discover(CASES_DIR);

describe("music-dsl conformance suite (TypeScript port)", () => {
  it("case count is frozen", () => {
    expect(cases.length).toBe(EXPECTED_CASE_COUNT);
  });
  for (const { relpath, case: c } of cases) {
    it(`${c.name} (${relpath})`, () => {
      const op = OPS[c.op];
      if (!op) throw new Error(`unknown op ${c.op} in ${c.name}`);
      expect(op(c.args)).toEqual(c.expect.value);
    });
  }
});
