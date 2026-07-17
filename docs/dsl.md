# The lead-sheet DSL

Tonalis's `tonalis` layer is a generic, **format-agnostic** lead-sheet / chord-chart
language. You write a harmony chart as plain text; a conformant implementation
reads that text and produces:

1. a canonical **AST** (`LeadSheet`), and
2. a list of **findings** (errors + warnings).

It is deliberately the pure *language layer*: it covers lexical structure,
document/header/body semantics, the chord grammar, the canonical AST, and the
findings codes — and emits **no** vendor file/URL format. Rendering the AST into
a specific notation-app format is the job of a separate downstream codec built on
top of this core.

!!! note "Normative reference"
    This page is an orientation. The authoritative contract is the **lead-sheet
    SPEC** at `conformance/leadsheet/SPEC.md` in the repository, and the
    machine-checkable case corpus under `conformance/leadsheet/cases/`. Where
    this prose and the spec disagree, the spec (and the blessed cases generated
    from the Python reference) win.

## Syntax at a glance

```
title: All The Things You Are
composer: Jerome Kern
key: Ab
time: 4/4

[A]
| F-7 | Bb7 | Eb^7 | Ab^7 |
| D-7 G7 | C^7 | C^7 | C^7 |
```

A document is a **header** followed by a **body**:

- **Header** — `key: value` per line. Required keys: `title`, `key`, `time`.
  Also recognized: `composer`, `style`. The body begins at the first line whose
  first character is `[`, `|`, or `{`.
- **Sections** — `[A]`, `[B]`, `[C]`, `[D]`, `[Intro]`/`[i]`, `[Verse]`/`[v]`,
  with an optional trailing integer (`[A2]`). Each carries a neutral `kind` role;
  a downstream codec maps that to its own section marker.
- **Measures** — `|`-separated. Multiple chords in one measure split the bar
  evenly; `chord:N` sets an explicit beat count.
- **Repeats & endings** — `{ ... }` is a repeat; `1.` / `2.` mark first/second
  endings; `Z` or `||` is a final barline.
- **Navigation** — `@segno`, `@coda`, `@tocoda`, `@fine`; `<text>` annotations;
  `@break` / `@newline` render hints; `[time: n/d]` mid-body meter changes.
- **No-chord** — `N.C.` (or `n`).

## Chord grammar

Chord quality uses glyphs, not words:

| Glyph | Meaning |
|-------|---------|
| `-`   | minor |
| `^`   | major-7 (`C^7`); bare `C^` is allowed |
| `o`   | diminished |
| `h`   | half-diminished |
| `+`   | augmented |
| `sus` | suspended |

Extensions include `b5 #5 6 b9 9 #9 11 #11 b13 13`, the `add\d+` form (`Cadd9`),
combined shorthand (`C69`), `alt` (`C7alt`), and slash bass (`D-/C`). The
spelled-out words `maj`/`min`/`dim`/`aug` are **rejected** — only the glyph forms
are valid.

The grammar is **permissive by design**: pathological-but-valid repeats such as
`C7777` and `Csussus` are accepted. Chord validity is defined by
`is_valid_chord`, which delegates to the `music_dsl` `Chord` parser (the
executable source of truth). See the [theory model](theory.md) for the parser
behind it.

## The AST

The IR is neutral — it stores no vendor-format detail:

```
LeadSheet  = { "schema_version": 1, "meta": Meta, "sections": [Section] }
Meta       = { "title"?: str, "composer"?: str, "style"?: str, "key"?: str, "time"?: [int,int] }
Section    = { "label": str, "kind": "a"|"b"|"c"|"d"|"intro"|"verse", "measures": [Measure] }
Measure    = { "cells": [Cell], "ending": int|null, "bar_open": bool,
               "barline": "normal"|"repeat_end"|"final", "nav": [NavItem],
               "hints": [str], "line": int }
Cell       = { "chord": str, "beats": int|null, "alt": str|null }
NavItem    = ["segno"] | ["coda"] | ["tocoda"] | ["fine"]
           | ["text", "<...>"] | ["time", [int, int]]
```

The projection round-trips losslessly (`from_json(to_json(ir)) == ir`) and the
canonical text printer re-flows layout so that `parse(serialize(ir)) == ir`
modulo source line numbers. Both round-trips, plus a canonical `text` golden, are
gated by the conformance suite on every AST-bearing case.

## Findings

The linter never throws on arbitrary input; malformed input becomes findings.
Findings are compared on `(code, severity, line)` only — message text is
non-normative and may differ between ports. An `error` finding means compilation
**fails**; a warning-only chart compiles successfully. The full findings-code
table (23 codes: `bad-chord`, `beat-sum`, `unbalanced-repeat`,
`missing-header`, …) is defined in §7 of the normative spec.
