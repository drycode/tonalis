# Quickstart

Tonalis is implemented three times. Pick the port that fits your stack — all
three expose the same public surface and pass the same conformance suite.

Every example below parses this chart:

```
title: All The Things You Are
composer: Jerome Kern
key: Ab
time: 4/4

[A]
| F-7 | Bb7 | Eb^7 | Ab^7 |
| D-7 G7 | C^7 | C^7 | C^7 |
```

## Python (`leadsheet/python/`)

Install (editable), then run the tests:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./leadsheet/python
pytest leadsheet/python/tests             # unit tests + import-boundary guard
pytest conformance/leadsheet/runners/python  # the 255-case conformance suite
```

First runnable example:

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

## TypeScript (`leadsheet/ts/`)

```bash
cd leadsheet/ts
npm ci
npm test          # units + import-boundary guard + the conformance suite
npm run typecheck
```

First runnable example:

```ts
import { parseDsl, lint, isValidChord, astToJson, serialize } from "tonalis";

const result = parseDsl(text);
const findings = [...result.findings, ...(result.chart ? lint(result.chart) : [])];
```

The TS port has **zero runtime dependencies** and is browser- and Node-safe.

## Rust (`leadsheet/rust/`)

```bash
cd leadsheet/rust
cargo test        # units + import-boundary guard + the conformance suite
```

First runnable example:

```rust
use tonalis::{parse_dsl, lint, is_valid_chord, serialize_text};
use tonalis::ast::ast_to_json;

let parsed = parse_dsl(text);
let chart = parsed.chart.unwrap();
let json = ast_to_json(&chart);
let printed = serialize_text(&chart);
```

The crate is `rlib`-only (no cdylib / wasm-bindgen target).

## The theory core (`music-dsl/`)

The lead-sheet language sits on top of the `music_dsl` theory core, which is a
separate package under `music-dsl/` with its own Python / TypeScript / Rust
ports. See the [theory model](theory.md) and [scale catalog](scales.md) pages
for what it exposes.
