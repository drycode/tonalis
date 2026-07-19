# tonalis

A generic, format-agnostic music-harmony DSL for lead sheets: parse chord
charts to a canonical AST, lint them with structured findings, and render back
to canonical text or JSON. The Rust port conforms to the same normative spec as
the Python reference and the TypeScript port via a shared 255-case conformance
suite.

Music-theory questions (chord validity, scales, keys) are delegated to the
pure [`music-dsl`](https://crates.io/crates/music-dsl) theory crate — the
package's only dependency.

## Install

```bash
cargo add tonalis
```

## Use

```rust
use tonalis::{parse_dsl, lint, is_valid_chord, ast_to_json};

let result = parse_dsl(&text);
if let Some(chart) = &result.chart {
    let findings = lint(chart);
    let json = ast_to_json(chart);
}
```

## Links

- Source, spec, docs, and conformance suite: <https://github.com/drycode/tonalis>
- License: MIT
