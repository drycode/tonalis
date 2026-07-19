/**
 * Port-level adversarial unit tests for the pure DSL parser/linter — complement the data-driven
 * conformance gate (../../conformance/tonalis/runners/ts/run.ts, wired in Task 8) with focused
 * regression checks. These exercise the PURE surface only (parseDsl + lint + isValidChord +
 * astToJson); URL-shaped assertions live in a downstream codec's compileDsl tests.
 */

import { describe, it, expect } from "vitest";
import { parseDsl, lint, isValidChord, astToJson } from "./index.js";
import { MAX_LINE_LEN, MAX_CHORD_TOKEN_LEN } from "./parser.js";

/** Collect all finding codes from parse + lint, the pure-surface analog of compileDsl().findings. */
function codes(dsl: string): string[] {
  const r = parseDsl(dsl);
  const findings = [...r.findings, ...(r.chart ? lint(r.chart) : [])];
  return findings.map((f) => f.code);
}

const SECTION_TOKEN_DSL = "title: T\nkey: C\ntime: 4/4\n[A]\n| C7 | F7 | C7 | C7 [B] Z\n";

describe("pure parser adversarial inputs", () => {
  it("does not read a trailing [B]-shaped token as a section (SECTION_RE is anchored)", () => {
    // CRITICAL-1: JS .exec is unanchored; without a leading anchor the `[B]` token in the last
    // measure would be misread as a section and every chord silently dropped. The anchor forces a
    // whole-line match, so `[B]` is an (invalid) chord token, not a section -> bad-chord.
    expect(codes(SECTION_TOKEN_DSL)).toContain("bad-chord");
  });

  it("caps the meter at MAX_METER (1000/4 -> bad-time)", () => {
    expect(codes("title: T\nkey: C\ntime: 1000/4\n[A]\n| C6 Z\n")).toContain("bad-time");
  });

  it("rejects non-ASCII / numeric-but-non-decimal digits", () => {
    // Arabic-Indic digit in time -> bad-time (ASCII-only digits, SPEC.md §1.1).
    expect(codes("title: T\nkey: C\ntime: ٣/٤\n[A]\n| C6 Z\n")).toContain("bad-time");
    // Superscript-2 :N -> bad-beats (the input that crashed the Python ref's int()).
    expect(codes("title: T\nkey: C\ntime: 4/4\n[A]\n| C:² Z\n")).toContain("bad-beats");
  });

  it("huge digit runs become findings, never errors/throws", () => {
    expect(codes("title: T\nkey: C\ntime: 4/4\n[A]\n| C:99999999999 Z\n")).toContain("bad-beats");
    expect(codes("title: T\nkey: C\ntime: 4/4\n[A]\n{ C |\n99999999999. D Z }\n")).toContain(
      "too-big",
    );
  });

  // Length caps must count CODE POINTS, not UTF-16 units — Python uses len() and Rust uses
  // chars().count() (both code-point counts). An astral char (U+1D11E G-clef) is 1 code point but
  // 2 UTF-16 units; counting .length would wrongly trip the cap at half the documented limit, so a
  // long astral line/token would be rejected by TS while Python/Rust accept it (port divergence).
  const ASTRAL = "\u{1D11E}"; // 1 code point, 2 UTF-16 units

  it("line-length cap counts code points, not UTF-16 units", () => {
    // A comment line is length-checked but produces no chord findings. Just under the cap (in code
    // points) must NOT trip "too-big", even though its UTF-16 .length is ~2x the limit.
    const underLine = "# " + ASTRAL.repeat(MAX_LINE_LEN - 2); // MAX_LINE_LEN code points
    expect(underLine.length).toBeGreaterThan(MAX_LINE_LEN); // UTF-16 units exceed the cap...
    expect([...underLine].length).toBe(MAX_LINE_LEN); // ...but code points equal it (accepted)
    expect(codes(`title: T\nkey: C\ntime: 4/4\n${underLine}\n[A]\n| C6 Z\n`)).not.toContain(
      "too-big",
    );
    // Just over the cap in code points IS rejected.
    const overLine = "# " + ASTRAL.repeat(MAX_LINE_LEN); // MAX_LINE_LEN + 2 code points
    expect(codes(`title: T\nkey: C\ntime: 4/4\n${overLine}\n[A]\n| C6 Z\n`)).toContain("too-big");
  });

  it("chord-token cap counts code points, not UTF-16 units", () => {
    // A token of MAX_CHORD_TOKEN_LEN astral code points is at the limit -> NOT "token-too-long"
    // (it is bad-chord, since astral chars aren't valid chords, but that's a different code).
    const atLimit = ASTRAL.repeat(MAX_CHORD_TOKEN_LEN);
    expect([...atLimit].length).toBe(MAX_CHORD_TOKEN_LEN);
    expect(atLimit.length).toBeGreaterThan(MAX_CHORD_TOKEN_LEN); // UTF-16 units exceed it
    expect(codes(`title: T\nkey: C\ntime: 4/4\n[A]\n| ${atLimit} Z\n`)).not.toContain(
      "token-too-long",
    );
    // One code point over the limit IS flagged token-too-long.
    const overLimit = ASTRAL.repeat(MAX_CHORD_TOKEN_LEN + 1);
    expect(codes(`title: T\nkey: C\ntime: 4/4\n[A]\n| ${overLimit} Z\n`)).toContain(
      "token-too-long",
    );
  });
});

describe("pure surface smoke", () => {
  it("isValidChord accepts real chords and rejects junk", () => {
    expect(isValidChord("C^7")).toBe(true);
    expect(isValidChord("A-7")).toBe(true);
    expect(isValidChord("[B]")).toBe(false);
  });

  it("astToJson projects a parsed chart deterministically", () => {
    const r = parseDsl("title: T\nkey: C\ntime: 4/4\n[A]\n| C^7 | A-7 | D-7 | G7 |\n");
    expect(r.chart).not.toBeNull();
    const json = astToJson(r.chart!);
    expect(json.meta.title).toBe("T");
    expect(json.sections.length).toBe(1);
    expect(json.sections[0]!.measures.length).toBe(4);
  });
});
