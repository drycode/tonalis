# tonalis

A generic, format-agnostic music-harmony DSL for lead sheets: parse chord
charts to a canonical AST, lint them with structured findings, and render back
to canonical text or JSON. This is the Python reference implementation;
TypeScript (`tonalis` on npm) and Rust (`tonalis` on crates.io) ports conform
to the same normative spec and a shared 255-case conformance suite.

Music-theory questions (chord validity, scales, keys) are delegated to the
pure [`music-dsl`](https://pypi.org/project/music-dsl/) theory library.

## Install

```bash
pip install tonalis
```

## Use

```python
from tonalis import parse_dsl, lint, serialize, to_json

result = parse_dsl(open("chart.txt").read())
findings = list(result.findings) + (lint(result.chart) if result.chart else [])
chart = result.chart            # a LeadSheet AST
json_obj = to_json(chart)       # canonical JSON (a dict)
text = serialize(chart)         # canonical text rendering
```

A small CLI is included: `python -m tonalis chart.txt` prints lint findings
(exit 1 if any error).

## Links

- Source, spec, docs, and conformance suite: <https://github.com/drycode/tonalis>
- License: MIT
