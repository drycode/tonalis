# Quickstart

Tonalis is implemented three times — a **Python** reference, a **TypeScript** port,
and a **Rust** port. All three expose the same public surface and pass the same
conformance suite, so pick the one that fits your stack. Choose a tab below; your
choice follows you across every code block on the site.

Every example parses this chart (save it as `chart.txt`):

```
title: All The Things You Are
composer: Jerome Kern
key: Ab
time: 4/4

[A]
| F-7 | Bb7 | Eb^7 | Ab^7 |
| D-7 G7 | C^7 | C^7 | C^7 |
```

## Install & first parse

=== "Python"

    ```bash
    pip install tonalis        # pulls in the music-dsl theory core
    ```

    ```python
    from tonalis import parse_dsl, lint, serialize, to_json

    result = parse_dsl(open("chart.txt").read())
    findings = list(result.findings) + (lint(result.chart) if result.chart else [])

    chart = result.chart      # a LeadSheet AST
    json_obj = to_json(chart) # canonical JSON (a dict)
    text = serialize(chart)   # canonical text rendering

    print(len(findings), "findings")          # -> 0 findings
    print(chart.sections[0].label)            # -> A
    print(json_obj["sections"][0]["measures"][0]["cells"][0]["chord"])  # -> F-7
    ```

    A small CLI ships with it: `python -m tonalis chart.txt` prints lint findings
    (exit 1 if any error).

=== "TypeScript"

    ```bash
    npm install tonalis        # zero runtime dependencies
    ```

    ```ts
    import { parseDsl, lint, astToJson, serialize } from "tonalis";

    const result = parseDsl(text);
    const findings = [...result.findings, ...(result.chart ? lint(result.chart) : [])];

    const chart = result.chart!;   // a LeadSheet AST
    const json = astToJson(chart); // canonical JSON
    const printed = serialize(chart);

    console.log(findings.length, "findings");   // -> 0 findings
    console.log(chart.sections[0].label);       // -> A
    ```

    The TS port has **zero runtime dependencies** and is browser- and Node-safe.
    It ships as ESM (`import`, not `require`).

=== "Rust"

    ```toml
    # Cargo.toml
    [dependencies]
    tonalis = "0.1"
    ```

    ```rust
    use tonalis::{parse_dsl, lint, serialize_text};
    use tonalis::ast::ast_to_json;

    let parsed = parse_dsl(text);
    let chart = parsed.chart.unwrap();   // a LeadSheet AST
    let json = ast_to_json(&chart);
    let printed = serialize_text(&chart);

    assert_eq!(chart.sections[0].label, "A");
    ```

    The crate is `rlib`-only (no cdylib / wasm-bindgen target).

## Building from source

Working on Tonalis itself, or want to run the conformance suite? The theory core
(`music-dsl/`) must be built first — `tonalis` depends on it.

=== "Python"

    ```bash
    python -m venv .venv && source .venv/bin/activate
    pip install -e "./music-dsl/python[dev]"   # theory core first
    pip install -e ./tonalis/python
    pytest tonalis/python/tests                # units + import-boundary guard
    pytest conformance/tonalis/runners/python  # the 255-case conformance suite
    ```

=== "TypeScript"

    ```bash
    cd music-dsl/ts && npm ci && npm run build  # theory core first
    cd ../../tonalis/ts && npm ci
    npm test                                    # units + guard + conformance
    npm run typecheck
    ```

=== "Rust"

    ```bash
    cd tonalis/rust
    cargo test                                  # units + guard + conformance
    ```

## Next

- [Lead-sheet DSL](dsl.md) — the chart language and a full [chart→AST worked example](dsl.md#chart-to-ast-a-worked-example).
- [Theory model](theory.md) — the `music_dsl` core the language sits on.
- [Scale catalog](scales.md) — all 39 scales and the two-tier diatonicity rules.
