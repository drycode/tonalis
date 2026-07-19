import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { isValidChord } from "./chords.js";

// One shared frozen oracle (tonalis/fixtures/chord_oracle.json), asserted by Python/TS/Rust alike.
// From tonalis/ts/src/ → ../../fixtures/ = tonalis/fixtures/.
const ORACLE: Record<string, boolean> = JSON.parse(
  readFileSync(fileURLToPath(new URL("../../fixtures/chord_oracle.json", import.meta.url)), "utf-8"),
);
const BLESSED = new Set<string>(["C7777"]); // old regex wrongly accepted; music_dsl correctly rejects.

describe("chord reconciliation (music_dsl validator vs frozen oracle)", () => {
  it("matches the oracle for every token except blessed", () => {
    const mismatches = Object.entries(ORACLE)
      .filter(([t, old]) => isValidChord(t) !== old && !BLESSED.has(t))
      .map(([t]) => t);
    expect(mismatches, `${mismatches.length} drift: ${mismatches.slice(0, 20).join(", ")}`).toEqual([]);
  });
  it("every blessed token is a live old=true / new=false divergence", () => {
    const stale = [...BLESSED].filter((t) => !(ORACLE[t] === true && isValidChord(t) === false));
    expect(stale, `stale blesses: ${stale.join(", ")}`).toEqual([]);
  });
});
