# Tonalis

**Parse a chord chart into a structured AST — in Python, TypeScript, or Rust, with
byte-for-byte identical results.** Tonalis is a spec-driven, polyglot music-theory
library: one normative conformance suite, three ports kept honest by a three-way
differential fuzzer.

[Quickstart](quickstart.md){ .md-button .md-button--primary }
[Lead-sheet DSL](dsl.md){ .md-button }
[View on GitHub](https://github.com/drycode/tonalis){ .md-button }

---

Write a harmony chart as plain text:

```
title: All The Things You Are
key: Ab
time: 4/4

[A]
| F-7 | Bb7 | Eb^7 | Ab^7 |
```

…and get back a canonical **AST**, a list of **lint findings**, a lossless **JSON**
projection, and a canonical **text** rendering — the same answers whichever port you
call. See it end to end in the [worked example](dsl.md#chart-to-ast-a-worked-example).

Under it sits the theory core's showpiece — **key-relative chords**. Write harmony
once as roman numerals and realize it into any key:

```python
ii = NumericChord.from_chord_string("ii-7")
ii.in_key(Notes.C)    # -> D-7
ii.in_key(Notes.Eb)   # -> F-7
```

## Two layers

<div class="grid cards" markdown>

-   **`music_dsl` — the theory core**

    ---

    Structured **chords** and, its centerpiece, **numeric (key-relative) chords** —
    a roman numeral that realizes to the right absolute chord in any key. Plus scale
    degrees, notes/intervals, and a 39-scale catalog as supporting tools.

    [→ Theory model](theory.md) · [→ Scale catalog](scales.md)

-   **`tonalis` — the lead-sheet language**

    ---

    A generic, **format-agnostic** chord-chart language. Pure *language layer* — it
    emits no vendor file or URL format; notation-app codecs are separate adapters
    built on this neutral core.

    [→ Lead-sheet DSL](dsl.md)

</div>

## Why it is built this way

The design rule is **one spec, three ports, no drift**.

![Tonalis architecture: one normative spec and conformance corpus generate blessed cases from the Python reference; Python, TypeScript, and Rust ports all implement the same surface; a differential fuzzer proves 0 divergences across the three.](assets/architecture.svg){ loading=lazy }

<div class="grid cards" markdown>

-   **One normative conformance suite**

    ---

    The contract is human-readable specs ([lead-sheet](dsl.md), [scales](scales.md))
    backed by a machine-checkable case corpus. Cases are **blessed from the Python
    reference** — that's what's authoritative, not any single port's code.

-   **Three implementations, identical behavior**

    ---

    Python (reference), TypeScript, and Rust each implement the same public surface
    and pass the same 255-case lead-sheet suite plus the theory conformance cases.

-   **A differential fuzzer keeps them honest**

    ---

    A seeded Python↔TS↔Rust fuzzer (`make fuzz`) drives the full chord-suffix grammar
    and the scale surface, and requires **0 divergences** across all three ports.

-   **Pick the port that fits your stack**

    ---

    The TS port has **zero runtime dependencies** and is browser- and Node-safe; the
    Rust crate is `rlib`-only (no cdylib / wasm-bindgen target). Same answers either way.

</div>

## What you get

- **Parse** DSL text → a `LeadSheet` AST (sections, measures, cells, repeats/endings, navigation).
- **Lint** → findings with `(code, severity, line)`; banned constructs produce an `error`-severity finding.
- **Validate** a single chord token (`is_valid_chord` / `isValidChord`).
- **AST ↔ JSON** — a canonical, fixed-key-order projection that round-trips losslessly.
- **AST → text** — a canonical printer; `parse(serialize(ir)) == ir` (modulo source line numbers), gated by conformance.
- **Theory model** — notes, intervals, chords, scale degrees, key-relative `NumericChord`s, and the 39-scale catalog.

## Where to go next

<div class="grid cards" markdown>

-   [**Quickstart**](quickstart.md) — install and a first runnable example, in all three ports.
-   [**Lead-sheet DSL**](dsl.md) — the chart language, chord grammar, and the chart→AST worked example.
-   [**Theory model**](theory.md) — chords and key-relative numeric chords (the centerpiece), plus scale degrees and notes.
-   [**Scale catalog**](scales.md) — all 39 scales and the two-tier diatonicity rules.
-   [**API reference**](api.md) — generated per-language API docs.

</div>

## License

MIT.
