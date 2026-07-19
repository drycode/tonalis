# Tonalis

A generic, format-agnostic music-harmony DSL. Write a chord/harmony lead sheet as plain text and
get back a structured **AST**, a list of **lint findings** (errors + warnings), a canonical **JSON**
projection of the AST, and a canonical **text** rendering.

Tonalis is the pure *language layer* — it parses and validates harmony notation and produces a
neutral abstract syntax tree. It is deliberately format-agnostic: it does not emit any vendor
file/URL format. Notation-format codecs (e.g. for a specific lead-sheet app) are separate adapters
built on top of this core.

The same language is implemented three times — in **Python**, **TypeScript**, and **Rust** — and all
three pass two shared, language-agnostic conformance suites: the **lead-sheet** suite (255 cases under
[`conformance/tonalis/`](conformance/tonalis/), specified in
[`conformance/tonalis/SPEC.md`](conformance/tonalis/SPEC.md)) and the **music-DSL scale/encode**
suite (429 cases under [`conformance/music-dsl/`](conformance/music-dsl/), specified in
[`conformance/music-dsl/SPEC-scales.md`](conformance/music-dsl/SPEC-scales.md)).

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
[`tonalis/python/tonalis/GRAMMAR.md`](tonalis/python/tonalis/GRAMMAR.md).

## Documentation

Full docs — concept guides, the scale catalog, and generated per-language API
references — are built with [mkdocs-material](https://squidfunk.github.io/mkdocs-material/)
from [`docs/`](docs/) and deploy to **GitHub Pages** (`.github/workflows/docs.yml`).

- **[Documentation site](https://drycode.github.io/tonalis/):** goes live when this
  repository is made public; the Pages **deploy** step is gated on that flip, while
  the docs **build** runs on every push to `main`.
- **Normative specs:** the [lead-sheet SPEC](conformance/tonalis/SPEC.md) and the
  [scale catalog SPEC](conformance/music-dsl/SPEC-scales.md).

Build the docs locally:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r docs/requirements.txt
bash docs/build_api.sh    # optional: generate the API references (needs pdoc/typedoc/cargo)
mkdocs serve              # or: mkdocs build --strict
```

## Test conventions

Where a new test goes, per port:

- **Python**: unit tests under `<pkg>/python/tests/unit/` (music-dsl further
  nests by domain); shared fixtures in `tests/fixtures/`; conformance runners
  live under `conformance/<pkg>/runners/python`.
- **TypeScript**: colocated `src/*.test.ts` next to the module under test.
- **Rust**: integration files in `<pkg>/rust/tests/` (`unit.rs`,
  `conformance.rs`, plus focused files like `two_tier.rs`).

The shared conformance corpora (`conformance/{music-dsl,tonalis}/cases/`) gate
all three ports; the seeded differential fuzzer covers the music-dsl surface
(the tonalis parser is corpus-gated only — its input space is line-oriented and
the 255-case corpus plus port-identical conformance keeps divergence bounded).

## Ports — install & test

### Python (`tonalis/python/`)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e "./music-dsl/python[dev]"   # theory library first: tonalis depends on
pip install -e ./tonalis/python            # music-dsl, which isn't on PyPI until publish
pytest tonalis/python/tests             # unit tests + import-boundary guard
pytest conformance/tonalis/runners/python  # the 255-case conformance suite
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

> Note: with your shell **at the repo root**, a bare `python -c "import tonalis"`
> picks up the `tonalis/` source directory (a namespace portion) instead of the
> installed package — run Python from any other directory (or via `pytest`,
> which is unaffected).

### TypeScript (`tonalis/ts/`)

```bash
cd music-dsl/ts && npm ci && npm run build   # theory lib first: tonalis resolves
cd ../../tonalis/ts                          # @tonalis/music-dsl against its dist/
npm ci
npm test          # units + import-boundary guard + the conformance suite
npm run typecheck
```

```ts
import { parseDsl, lint, isValidChord, astToJson, serialize } from "tonalis";

const result = parseDsl(text);
const findings = [...result.findings, ...(result.chart ? lint(result.chart) : [])];
```

The TS port's only runtime dependency is `@tonalis/music-dsl` (linked in-repo via
`file:`, so `npm ci` needs no registry access; the publish workflow rewrites it to
the published version range).

### Rust (`tonalis/rust/`)

```bash
cd tonalis/rust
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
