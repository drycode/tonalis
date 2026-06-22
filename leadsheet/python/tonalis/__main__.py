import argparse
import sys

from tonalis.parser import parse_dsl
from tonalis.lint import lint


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tonalis", description="Lint/parse a lead-sheet DSL chart.")
    ap.add_argument("file")
    ap.add_argument("--lint-only", action="store_true")
    args = ap.parse_args(argv)
    try:
        text = open(args.file, encoding="utf-8").read()
    except OSError as e:
        print(f"error: cannot read {args.file}: {e}", file=sys.stderr)
        return 2
    pr = parse_dsl(text)
    findings = list(pr.findings) + (lint(pr.chart) if pr.chart else [])
    for f in findings:
        print(f"{f.severity}:{f.line}: [{f.code}] {f.message}", file=sys.stderr)
    return 1 if any(f.severity == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
