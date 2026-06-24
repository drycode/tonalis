/**
 * Import-boundary guard (TS) — the dsl-core half of the §7 one-way-dependency invariant.
 *
 * Statically scans every `dsl-core/ts/src/**` module's import/export specifiers and forbids any
 * cross-package reach: no `../ireal-codec`, no `../text-target`, no bare third-party package import
 * (the pure language core has ZERO runtime deps). Only relative-WITHIN-package specifiers (`./...`
 * that don't climb out of `src/`) are allowed; `vitest` and type-only imports are allowed in test
 * files. The compiler-as-guard (TS path resolution) would already fail a broken `../ireal-codec`
 * import, but this test makes the invariant explicit + fails loudly with the offending file.
 *
 * A NEGATIVE block proves the guard BITES: it runs the same specifier classifier over synthetic
 * forbidden specifiers and asserts each is flagged (the real src is never modified).
 */
import { describe, it, expect } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url)); // dsl-core/ts/src
const SRC_ROOT = HERE;

/** Recursively list .ts files under dir. */
function listTs(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...listTs(p));
    else if (name.endsWith(".ts")) out.push(p);
  }
  return out;
}

/** Extract every static import/export-from specifier string from TS source.
 *
 * The statement-start anchor is `(?:^|[\n;{}])` — line-start OR after a `;`/`{`/`}` — NOT just
 * `(?:^|\n)`. A bare `(?:^|\n)` anchor has a real HOLE: a SECOND import on the same physical line
 * (`import a from "./ast.js"; import b from "../ireal-codec";`) starts after a `;`, not a newline,
 * so the forbidden second specifier is silently skipped (the TS-analogue of Python's multi-alias
 * `import os, SCRUBBED` hole). Anchoring on `;`/`{`/`}` too closes it.
 */
function specifiers(source: string): string[] {
  const out: string[] = [];
  // import ... from "X";  /  export ... from "X";  /  import "X";  /  import type ... from "X"
  const re = /(?:^|[\n;{}])\s*(?:import|export)\b[^;'"]*?from\s*["']([^"']+)["']/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(source)) !== null) out.push(m[1]!);
  const bareRe = /(?:^|[\n;{}])\s*import\s*["']([^"']+)["']/g;
  while ((m = bareRe.exec(source)) !== null) out.push(m[1]!);
  // dynamic import("X")
  const dynRe = /\bimport\s*\(\s*["']([^"']+)["']\s*\)/g;
  while ((m = dynRe.exec(source)) !== null) out.push("DYNAMIC:" + m[1]!);
  return out;
}

const ALLOWED_BARE = new Set<string>(["vitest"]); // test runner only; allowed in *.test.ts
// Phase 3: the one-way leadsheet → music_dsl theory-lib dependency. Unlike vitest (a dev-only
// test dep), this is a PRODUCTION runtime dep — allowed from any file (incl. chords.ts), so it is
// NOT gated on isTest. Exact-membership one-entry set: not a blanket bare-import pass.
const ALLOWED_RUNTIME_DEP = new Set<string>(["music_dsl"]);

/**
 * Classify one specifier from a file. Returns a violation string, or null if allowed.
 * `isTest` relaxes the rule to permit the vitest import.
 */
function classify(spec: string, fileAbsPath: string, isTest: boolean): string | null {
  if (spec.startsWith("DYNAMIC:")) {
    return `dynamic import(${JSON.stringify(spec.slice(8))}) is forbidden in dsl-core/ts/src`;
  }
  if (spec.startsWith("node:")) return null; // node stdlib (used only by this guard test itself)
  if (spec.startsWith(".")) {
    // relative — must NOT climb out of src/ (no ../ireal-codec, ../text-target, ../../anything)
    const target = resolve(dirname(fileAbsPath), spec);
    if (!target.startsWith(SRC_ROOT)) {
      return `relative import "${spec}" escapes dsl-core/ts/src (cross-package reach)`;
    }
    return null;
  }
  // bare specifier (a package).
  if (ALLOWED_RUNTIME_DEP.has(spec)) return null; // production runtime dep, allowed in any file
  if (isTest && ALLOWED_BARE.has(spec)) return null; // vitest: dev test dep, test files only
  return `bare package import "${spec}" is forbidden (only music_dsl runtime + vitest in tests)`;
}

describe("dsl-core/ts import boundary", () => {
  it("no src module reaches outside dsl-core/ts/src (no ../ireal-codec, ../text-target, bare deps)", () => {
    const violations: string[] = [];
    for (const file of listTs(SRC_ROOT)) {
      // This guard file itself contains forbidden-looking specifier STRINGS as negative-test
      // fixtures (e.g. "import(...)" / "../ireal-codec"); excluding it avoids scanning its fixtures.
      if (file.endsWith("boundary.test.ts")) continue;
      const isTest = file.endsWith(".test.ts");
      const src = readFileSync(file, "utf-8");
      for (const spec of specifiers(src)) {
        const v = classify(spec, file, isTest);
        if (v) violations.push(`${file}: ${v}`);
      }
    }
    expect(violations, violations.join("\n")).toEqual([]);
  });

  // NEGATIVE: prove the guard BITES on forbidden specifiers (the classifier is not a no-op).
  it("flags a cross-package ../ireal-codec import", () => {
    const fake = join(SRC_ROOT, "parser.ts");
    expect(classify("../../../ireal-codec/ts/src/index.js", fake, false)).not.toBeNull();
  });
  it("flags a cross-package ../text-target import", () => {
    const fake = join(SRC_ROOT, "parser.ts");
    expect(classify("../../text-target/render.js", fake, false)).not.toBeNull();
  });
  it("flags a bare third-party package import", () => {
    const fake = join(SRC_ROOT, "parser.ts");
    expect(classify("ireal-codec", fake, false)).not.toBeNull();
  });
  it("flags a dynamic import()", () => {
    const fake = join(SRC_ROOT, "parser.ts");
    expect(classify("DYNAMIC:../ireal-codec", fake, false)).not.toBeNull();
  });
  it("ALLOWS a relative within-package import (sanity: guard isn't always-failing)", () => {
    const fake = join(SRC_ROOT, "index.ts");
    expect(classify("./ast.js", fake, false)).toBeNull();
  });
  it("ALLOWS vitest only in a test file", () => {
    const fake = join(SRC_ROOT, "x.test.ts");
    expect(classify("vitest", fake, true)).toBeNull();
    expect(classify("vitest", join(SRC_ROOT, "x.ts"), false)).not.toBeNull();
  });
  it("ALLOWS the music_dsl runtime dep from production source", () => {
    const fake = join(SRC_ROOT, "chords.ts");
    expect(classify("music_dsl", fake, false)).toBeNull();
  });
  it("still flags an unapproved bare dep from production source", () => {
    const fake = join(SRC_ROOT, "chords.ts");
    expect(classify("lodash", fake, false)).not.toBeNull();
  });

  // NEGATIVE: the same-line second-import hole. `import a from "./ast.js"; import b from
  // "../ireal-codec";` starts the 2nd statement after a `;`, not a newline — a `(?:^|\n)`-anchored
  // scanner skips it. The fixed `(?:^|[\n;{}])` anchor must surface BOTH specifiers so the forbidden
  // cross-package reach is flagged.
  it("surfaces a SECOND same-line import after a semicolon (multi-specifier hole)", () => {
    const src = 'import a from "./ast.js"; import b from "../../../ireal-codec/index.js";';
    const specs = specifiers(src);
    expect(specs).toContain("./ast.js");
    expect(specs).toContain("../../../ireal-codec/index.js");
    const fake = join(SRC_ROOT, "parser.ts");
    const flagged = specs.map((s) => classify(s, fake, false)).filter((v) => v !== null);
    expect(flagged.length).toBeGreaterThan(0); // the forbidden second import IS caught
  });

  it("surfaces a SECOND same-line BARE import after a semicolon", () => {
    const src = 'import "./side.js"; import "../../../ireal-codec/side.js";';
    const specs = specifiers(src);
    expect(specs).toContain("./side.js");
    expect(specs).toContain("../../../ireal-codec/side.js");
  });
});
