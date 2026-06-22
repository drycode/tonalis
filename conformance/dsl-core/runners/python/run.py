"""dsl-core Python reference conformance runner (the pure language).

Discovers every ``conformance/dsl-core/cases/**/*.json``, parses+lints each case's ``dsl`` with the
``tonalis`` reference, and asserts per the SPEC.md §0.1 hierarchy:

  - ``ast``      OPTIONAL, deep-equal canonical LeadSheet JSON when present
  - ``findings`` compared on (code, severity, line) only, order-independent

There is NO ``url`` assertion here — the iReal URL is the codec suite's concern
(``conformance/ireal-codec/runners/python/run.py``).

Runnable two ways:
  - standalone: ``python conformance/dsl-core/runners/python/run.py``  (prints PASS/FAIL summary)
  - via pytest: ``conformance/dsl-core/runners/python/test_run.py`` subprocess-invokes it
"""

import json
from pathlib import Path

from tonalis.lint import lint
from tonalis.parser import parse_dsl
from tonalis.serialize import ast_from_json, ast_to_json
from tonalis.serialize_text import serialize

# this file: <repo>/conformance/dsl-core/runners/python/run.py
#   parents[0]=python  parents[1]=runners  parents[2]=dsl-core
CONFORMANCE_DIR = Path(__file__).resolve().parents[2]
CASES_DIR = CONFORMANCE_DIR / "cases"


def discover_cases(cases_dir: Path = CASES_DIR):
    """Yield (relpath_str, case_dict) for every case JSON, sorted for stable ids."""
    for path in sorted(cases_dir.rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        yield str(path.relative_to(cases_dir)), data


def _finding_keys(findings):
    return sorted((f["code"], f["severity"], f["line"]) for f in findings)


def _norm_lines(chart):
    """Zero each measure's ``line`` source-position artifact for text round-trip identity.

    The canonical printer re-flows the layout (a blank line before each section), so absolute
    source-line numbers shift while every semantic field is preserved. ``IR->text->IR`` therefore
    compares lead-sheet semantics with ``line`` normalized; ``IR->JSON->IR`` keeps ``line`` (the
    JSON carries it verbatim). Mirrors the TS/Rust serialize tests and Python test_serialize_text.
    """
    if chart is not None:
        for s in chart.sections:
            for m in s.measures:
                m.line = 0
    return chart


def run_case(case: dict):
    """Run one case against the reference. Returns a list of failure strings ([] = pass)."""
    failures = []
    dsl = case["dsl"]
    expect = case["expect"]

    pr = parse_dsl(dsl)
    # lint() mirrors the bless path (lint is pure wrt the AST); collect parse + lint findings.
    lint_findings = lint(pr.chart) if pr.chart is not None else []
    all_findings = list(pr.findings) + list(lint_findings)

    # findings: (code, severity, line) only, order-independent
    if "findings" in expect:
        actual = _finding_keys(
            {"code": f.code, "severity": f.severity, "line": f.line} for f in all_findings
        )
        wanted = _finding_keys(expect["findings"])
        if actual != wanted:
            failures.append(
                f"findings mismatch:\n   expected: {wanted}\n   actual:   {actual}"
            )

    # ast: optional deep-equal of the canonical JSON
    if expect.get("ast") is not None:
        if pr.chart is not None:
            actual_ast = ast_to_json(pr.chart)
        else:
            actual_ast = None
        if actual_ast != expect["ast"]:
            failures.append("ast mismatch (canonical neutral JSON deep-equality failed)")

    # round-trips + canonical text golden (only meaningful when there's a parseable chart)
    if pr.chart is not None:
        # IR -> JSON -> IR identity is lossless (JSON carries `line` verbatim), so it holds for
        # ANY parseable chart, including the degenerate findings-only/banned inputs.
        if ast_from_json(ast_to_json(pr.chart)) != pr.chart:
            failures.append("IR->JSON->IR round-trip is not identity")
        # IR -> text -> IR identity + text golden are asserted ONLY for the canonical-form cases
        # (those the bless tool gave a `text` golden — i.e. ast-bearing cases). Banned/degenerate
        # inputs (e.g. an over-long space-separated alt group) are not canonical DSL and carry no
        # text golden; their lint behavior is asserted via `findings`, not a text round-trip.
        if expect.get("text") is not None:
            if serialize(pr.chart) != expect["text"]:
                failures.append("text golden mismatch (canonical DSL serialization)")
            # the printer re-flows layout, so compare `line`-normalized
            reparsed = parse_dsl(serialize(pr.chart)).chart
            if _norm_lines(reparsed) != _norm_lines(parse_dsl(dsl).chart):
                failures.append("IR->text->IR round-trip is not identity")

    return failures


def main() -> int:
    total = passed = 0
    fails = []
    for relpath, case in discover_cases():
        total += 1
        f = run_case(case)
        if f:
            fails.append((relpath, case.get("name", relpath), f))
        else:
            passed += 1
    for relpath, name, f in fails:
        print(f"FAIL {name} ({relpath})")
        for line in f:
            print(f"   {line}")
    print(f"\n{passed}/{total} dsl-core conformance cases passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
