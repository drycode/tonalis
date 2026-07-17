/**
 * leadsheet TypeScript conformance runner (vitest suite).
 *
 * Discovers every `conformance/leadsheet/cases/**\/*.json`, parses+lints each case's `dsl` with the
 * TS port, and asserts per the SPEC.md §0.1 hierarchy:
 *
 *   - `ast`      OPTIONAL, deep-equal canonical LeadSheet JSON when present
 *   - `findings` compared on (code, severity, line) only, order-independent
 *
 * There is NO `url` assertion here — any vendor-format URL is out of scope here; it is a
 * downstream codec's concern. Mirrors the Python runner. Node-only APIs
 * (fs/path/url) are confined to this test harness — the core `leadsheet/ts/src` package stays
 * browser-safe.
 */

import { describe, it, expect } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";

import {
  parseDsl,
  lint,
  astToJson,
  astFromJson,
  serialize,
  type LeadSheet,
} from "tonalis";

const HERE = dirname(fileURLToPath(import.meta.url));
// conformance/leadsheet/runners/ts -> conformance/leadsheet/cases
const CASES_DIR = join(HERE, "..", "..", "cases");

interface ExpectedFinding {
  code: string;
  severity: string;
  line: number;
}

interface Case {
  name: string;
  tags?: string[];
  dsl: string;
  expect: {
    ast?: unknown;
    findings?: ExpectedFinding[];
    text?: string;
  };
}

/**
 * Zero each measure's `line` source-position artifact for text round-trip identity. The canonical
 * printer re-flows the layout (a blank line before each section), so absolute source-line numbers
 * shift while every semantic field is preserved. `IR->text->IR` compares `line`-normalized;
 * `IR->JSON->IR` keeps `line`. Mirrors the Python runner + serializeText.test.ts.
 */
function normLines(chart: LeadSheet): LeadSheet {
  for (const s of chart.sections) for (const m of s.measures) m.line = 0;
  return chart;
}

function discoverCases(dir: string): Array<{ relpath: string; case: Case }> {
  const out: Array<{ relpath: string; case: Case }> = [];
  const walk = (d: string): void => {
    for (const entry of readdirSync(d).sort()) {
      const full = join(d, entry);
      if (statSync(full).isDirectory()) walk(full);
      else if (entry.endsWith(".json")) {
        const data = JSON.parse(readFileSync(full, "utf-8")) as Case;
        out.push({ relpath: relative(CASES_DIR, full), case: data });
      }
    }
  };
  walk(dir);
  out.sort((a, b) => (a.relpath < b.relpath ? -1 : a.relpath > b.relpath ? 1 : 0));
  return out;
}

function findingKeys(
  findings: Array<{ code: string; severity: string; line: number }>,
): string[] {
  return findings.map((f) => `${f.code} ${f.severity} ${f.line}`).sort();
}

const cases = discoverCases(CASES_DIR);

describe("leadsheet conformance suite (TypeScript port)", () => {
  if (cases.length === 0) {
    it("found conformance cases", () => {
      throw new Error(`no leadsheet conformance cases discovered under ${CASES_DIR}`);
    });
  }

  for (const { relpath, case: c } of cases) {
    it(`${c.name} (${relpath})`, () => {
      const pr = parseDsl(c.dsl);
      // lint() mirrors the bless path; collect parse + lint findings.
      const lintFindings = pr.chart !== null ? lint(pr.chart) : [];
      const allFindings = [...pr.findings, ...lintFindings];

      // findings: (code, severity, line) only, order-independent
      if (c.expect.findings !== undefined) {
        const actual = findingKeys(allFindings);
        const wanted = findingKeys(c.expect.findings);
        expect(actual, `findings mismatch for ${c.name}`).toEqual(wanted);
      }

      // ast: optional deep-equal of the canonical JSON
      if (c.expect.ast != null) {
        let actualAst: unknown = null;
        if (pr.chart !== null) {
          actualAst = astToJson(pr.chart);
        }
        expect(actualAst, `ast mismatch for ${c.name}`).toEqual(c.expect.ast);
      }

      // round-trips + canonical text golden (only meaningful when there's a parseable chart)
      if (pr.chart !== null) {
        // IR -> JSON -> IR identity is lossless (JSON carries `line`), so it holds for ANY
        // parseable chart, including degenerate findings-only/banned inputs.
        expect(
          astFromJson(astToJson(pr.chart)),
          `IR->JSON->IR for ${c.name}`,
        ).toEqual(pr.chart);
        // IR -> text -> IR identity + text golden are asserted ONLY for canonical-form cases
        // (those the bless tool gave a `text` golden); banned/degenerate inputs carry none.
        if (c.expect.text !== undefined) {
          expect(serialize(pr.chart), `text golden for ${c.name}`).toBe(c.expect.text);
          const reparsed = parseDsl(serialize(pr.chart)).chart;
          expect(
            reparsed === null ? null : normLines(reparsed),
            `IR->text->IR for ${c.name}`,
          ).toEqual(normLines(parseDsl(c.dsl).chart!));
        }
      }
    });
  }
});
