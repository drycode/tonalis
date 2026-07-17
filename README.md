# Tonalis

A generic, format-agnostic music-harmony DSL. Write a chord/harmony lead sheet as plain text and
get back a structured **AST**, a list of **lint findings** (errors + warnings), a canonical **JSON**
projection of the AST, and a canonical **text** rendering.

Tonalis is the pure *language layer* — it parses and validates harmony notation and produces a
neutral abstract syntax tree. It is deliberately format-agnostic: it does not emit any vendor
file/URL format. Notation-format codecs (e.g. for a specific lead-sheet app) are separate adapters
built on top of this core.

The same language is implemented three times — in **Python**, **TypeScript**, and **Rust** — and all
three pass one shared, language-agnostic conformance suite (255 cases under
[`conformance/leadsheet/`](conformance/leadsheet/), specified in
[`conformance/leadsheet/SPEC.md`](conformance/leadsheet/SPEC.md)).

## What it does

For each port the public surface is the same:

- **parse** DSL text → a `LeadSheet` AST (sections, measures, cells, repeats/endings, navigation).
- **lint** → a list of findings with `(code, severity, line)`; banned constructs produce an
  `error`-severity finding.
- **validate a single chord token** (`is_valid_chord` / `isValidChord`).
- **AST ↔ JSON** — a canonical, fixed-key-order JSON projection (`ast_to_json` / `astToJson`,
  `ast_from_json` / `astFromJson`).
- **AST → text** — a canonical text printer (`serialize`); `parse(serialize(ir)) == ir` (modulo
  source line numbers) is gated by the conformance suite.

## Syntax example

```
title: All The Things You Are
composer: Jerome Kern
key: Ab
time: 4/4

[A]
| F-7 | Bb7 | Eb^7 | Ab^7 |
| D-7 G7 | C^7 | C^7 | C^7 |
```

A header (`key: value` per line; required keys `title`, `key`, `time`), then `[Section]` labels and
`|`-separated measures. Multiple chords in one measure split the bar evenly; `:N` sets an explicit
beat count. `{ ... }` is a repeat, `1.`/`2.` mark first/second endings, and `@segno` / `@coda` /
`@tocoda` / `@fine` express navigation. Chord quality uses `-` (minor), `^` (major-7), `o` (dim),
`h` (half-dim), `+` (aug), `sus`; extensions include `b5 #5 6 b9 9 #9 11 #11 b13 13`; `N.C.` is
no-chord. The full grammar lives in
[`leadsheet/python/tonalis/GRAMMAR.md`](leadsheet/python/tonalis/GRAMMAR.md).

## Documentation

Full docs — concept guides, the scale catalog, and generated per-language API
references — are built with [mkdocs-material](https://squidfunk.github.io/mkdocs-material/)
from [`docs/`](docs/) and deploy to **GitHub Pages** (`.github/workflows/docs.yml`).

- **Site (once public):** `https://<org>.github.io/tonalis/` — the URL goes live
  when this repository is made public; the Pages **deploy** step is gated on that
  flip, while the docs **build** runs on every push to `main`.
- **Normative specs:** the [lead-sheet SPEC](conformance/leadsheet/SPEC.md) and the
  [scale catalog SPEC](conformance/music-dsl/SPEC-scales.md).

Build the docs locally:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r docs/requirements.txt
bash docs/build_api.sh    # optional: generate the API references (needs pdoc/typedoc/cargo)
mkdocs serve              # or: mkdocs build --strict
```

## Ports — install & test

### Python (`leadsheet/python/`)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./leadsheet/python
pytest leadsheet/python/tests             # unit tests + import-boundary guard
pytest conformance/leadsheet/runners/python  # the 255-case conformance suite
```

```python
from tonalis import parse_dsl, lint, serialize, to_json

result = parse_dsl(open("chart.txt").read())
findings = list(result.findings) + (lint(result.chart) if result.chart else [])
chart = result.chart            # a LeadSheet AST
json_obj = to_json(chart)       # canonical JSON (a dict)
text = serialize(chart)         # canonical text rendering
```

A small CLI is included: `python -m tonalis chart.txt` prints lint findings (exit 1 if any error).

### TypeScript (`leadsheet/ts/`)

```bash
cd leadsheet/ts
npm ci
npm test          # units + import-boundary guard + the conformance suite
npm run typecheck
```

```ts
import { parseDsl, lint, isValidChord, astToJson, serialize } from "tonalis";

const result = parseDsl(text);
const findings = [...result.findings, ...(result.chart ? lint(result.chart) : [])];
```

The TS port has **zero runtime dependencies** and is browser- and Node-safe.

### Rust (`leadsheet/rust/`)

```bash
cd leadsheet/rust
cargo test        # units + import-boundary guard + the conformance suite
```

```rust
use tonalis::{parse_dsl, lint, is_valid_chord, serialize_text};
use tonalis::ast::ast_to_json;

let parsed = parse_dsl(text);
let chart = parsed.chart.unwrap();
let json = ast_to_json(&chart);
let printed = serialize_text(&chart);
```

The crate is `rlib`-only (no cdylib / wasm-bindgen target).

## License

MIT — see [LICENSE](LICENSE).
