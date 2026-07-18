# Tonalis

**A spec-driven, polyglot music-theory library.** Tonalis is one normative
conformance suite with three ports — a **Python** reference implementation, a
**TypeScript** port, and a **Rust** port — kept byte-for-byte in lockstep by a
shared, language-agnostic test corpus and a three-way differential fuzzer.

It has two layers:

- **`music_dsl`** — the theory core: notes, intervals, chords, numeric
  (key-relative) chords, scale degrees, and a 39-scale catalog with a two-tier
  diatonicity model.
- **`tonalis`** (leadsheet) — a generic, format-agnostic lead-sheet / chord-chart
  language. Write a harmony chart as plain text and get back a structured
  **AST**, a list of **lint findings** (errors + warnings), a canonical **JSON**
  projection, and a canonical **text** rendering.

Tonalis is deliberately the pure *language layer*. It does not emit any vendor
file or URL format; notation-app codecs are separate adapters built on top of
this neutral core.

## Why it is built this way

The design rule is **one spec, three ports, no drift**:

- **One normative conformance suite.** The contract lives as human-readable
  normative specs ([lead-sheet SPEC](dsl.md), [scale SPEC](scales.md)) backed by
  a machine-checkable case corpus under `conformance/`. The blessed cases —
  generated from the Python reference — are authoritative.
- **Three implementations, identical behavior.** Python (reference),
  TypeScript, and Rust each implement the same public surface and pass the same
  255-case lead-sheet suite plus the music-theory conformance cases.
- **A differential fuzzer keeps them honest.** A seeded Python↔TS↔Rust fuzzer
  (`make fuzz`) generates inputs across the full chord-suffix grammar and the
  scale surface, and requires **0 divergences** across all three ports.

The result: pick the port that fits your stack and get the same answers. The TS
port has **zero runtime dependencies** and is browser- and Node-safe; the Rust
crate is `rlib`-only (no cdylib / wasm-bindgen target).

## Features

- **Parse** DSL text → a `LeadSheet` AST (sections, measures, cells,
  repeats/endings, navigation).
- **Lint** → findings with `(code, severity, line)`; banned constructs produce an
  `error`-severity finding.
- **Validate** a single chord token (`is_valid_chord` / `isValidChord`).
- **AST ↔ JSON** — a canonical, fixed-key-order JSON projection that round-trips
  losslessly.
- **AST → text** — a canonical text printer; `parse(serialize(ir)) == ir`
  (modulo source line numbers) is gated by the conformance suite.
- **Theory model** — notes/intervals/chords/scale degrees, key-relative
  `NumericChord`s, and a 39-scale catalog with membership vs. functional
  (diatonic) queries cleanly separated.

## Where to go next

- [Quickstart](quickstart.md) — install and a first runnable example for Python,
  TypeScript, and Rust.
- [Lead-sheet DSL](dsl.md) — the chart language and a pointer to the normative
  spec.
- [Theory model](theory.md) — notes, intervals, chords, scale degrees, numeric
  chords.
- [Scale catalog](scales.md) — the full 39-scale catalog and the two-tier
  diatonicity rules (the flagship reference).
- [API reference](api.md) — generated per-language API docs.

## License

MIT.
