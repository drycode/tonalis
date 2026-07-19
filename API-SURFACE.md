# Tonalis — public API surface

Inventory of the exported/public surface per package per language, as of the
`Tonalis OSS public-readiness` baseline (DRY-405, 2026-07-17). This is the reference the
Phase-1 audit (DRY-406) reviews against and the Phase-3 scale work (DRY-411/412) extends.

> **Phase-3 target (scale surface), flagged here:** `Scales`, `is_diatonic`,
> `harmonic_function_in_key`, `scan_scale`, `scale_pitches`, `scale_degree_pitch`.
> These are the symbols the two-tier diatonicity model + exhaustive catalog will reshape
> across all three ports. Today `Scales` has exactly three members (Major, Minor,
> HarmonicMinor).

## Package: `music_dsl` (theory core — `music-dsl/`)

### Python (`music-dsl/python/music_dsl/`)
Top-level (`__init__`): `Key` (dataclass: root, scale), `Notes`, `Scales`, `__version__`.
Public surface is largely submodule-scoped:
- `domain/static/notes.py`: `Notes`, `Intervals`
- `domain/static/scale_degree.py`: `ScaleDegree`
- `domain/chords/`: `Chord`, `NumericChord`, `AbstractChord`; `chord.py`: `HarmonicFunctions`, `Triad`, `Seventh`, `Extensions`
- `encode.py`: `Encoding`, **`Scales`**, `scan_scale`
- `transactions.py`: `normalize_to_c`, `modulate`, **`harmonic_function_in_key`**, **`is_diatonic`**, `chord_in_key`
- `realize.py`: `note_to_midi`, `midi_to_hz`, `note_to_hz`, `interval_pitches`, `chord_pitches`, **`scale_pitches`**, **`scale_degree_pitch`**

### TypeScript (`music-dsl/ts/src/index.ts`)
Re-exports: `Note`/`TWELVE_TONES`/`noteValue`/`noteFromValue`/`noteToFlat`/`notesEqual`/`noteIndex`;
`IntervalName`/`intervalSemitones`/`intervalsEqual`; `ScaleDegreeT`/`SCALE_DEGREES`/`scaleDegreesEqual`/`scaleDegreeIndex`;
`HarmonicFunction`/`Triad`/`Seventh`/`Extensions`; `MIN_SUPPORTED`/`MAX_SUPPORTED`/`stripLeft`/`stripRight`/`semitonesApartAscending`;
`EMPTY_CHORD_ENCODING`/`DIMINISHED_ENCODING`/**`Scales`**/`scaleValue`/`encodingValue`;
`parseChord`/`ChordModel`/`InvalidChordStringError`; and the transactions/realize surface (incl. **`isDiatonic`**, **`harmonicFunctionInKey`**). Zero runtime deps.

### Rust (`music-dsl/rust/src/lib.rs`)
`pub mod`: chord, chord_quality, encode, get_index, helpers, measure, notes, numeric_chord, realize, scale_degree, transactions.
`pub use`: `chord_encoding`/`parse_chord`/`ChordModel`…; `Extensions`/`HarmonicFunction`/`Seventh`/`Triad`;
`encode::{… Scales …}`; `strip_left`/`strip_right`/`semitones_apart_ascending`; `parse_measure`/`MeasureModel`/`TimeSignature`;
`Note`; `numeric_from_chord`/`parse_numeric`/`NumericChordAttrs`; `chord_pitches`/`interval_pitches`/`midi_to_hz`/`note_to_midi`…;
`ScaleDegree`; `transactions::{chord_in_key, harmonic_function_in_key, is_diatonic, modulate …}`; plus the `Interval` enum. rlib-only (no cdylib/wasm-bindgen).

## Package: `tonalis` (lead-sheet language — `tonalis/`)

### Python (`tonalis/python/tonalis/`)
`__all__`: `parse_dsl`, `lint`, `is_valid_chord`, `serialize`, `ast_to_json`, `ast_from_json`, `to_json`, `from_json`,
`LeadSheet`, `Cell`, `Measure`, `Section`, `SectionKind`, `Barline`, `LintFinding`, `ParseResult`. CLI: `python -m tonalis`.

### TypeScript (`tonalis/ts`, package `tonalis`)
`parseDsl`, `lint`, `isValidChord`, `astToJson`, `serialize` (+ AST types). Zero runtime deps; browser/Node-safe.

### Rust (`tonalis/rust`, crate `tonalis`)
`parse_dsl`, `lint`, `is_valid_chord`, `serialize_text`, `ast::ast_to_json`. rlib-only.

## Conformance (`conformance/`)
Data-driven cross-port suites (`music-dsl/`, `tonalis/`) + the normative `SPEC.md`, blessed from the
Python reference. Runners per language; a Python↔TS↔Rust differential fuzzer under
`conformance/music-dsl/fuzz/` (`make fuzz` / `make fuzz-seed2`).

---

## Green baseline (DRY-405, 2026-07-17)

Commands run from repo root (`.venv/bin/python`; `PYTHON=.venv/bin/python` for the fuzzer):

| Suite | Command | Result |
|-------|---------|--------|
| music-dsl python | `pytest music-dsl/python/tests` | **360 passed** |
| leadsheet python | `pytest tonalis/python/tests` | **97 passed** |
| conformance python | `pytest conformance/{music-dsl,tonalis}/runners/python` | **5 passed** |
| music-dsl ts | `npm test` (music-dsl/ts) | **452 passed** |
| music-dsl ts typecheck | `npx tsc --noEmit` | **clean** |
| leadsheet ts | `npm test` (tonalis/ts) | **294 passed** |
| music-dsl rust | `cargo test` | **49 passed, 0 failed** |
| leadsheet rust | `cargo test` | **13 passed, 0 failed** |
| differential fuzzer | `make fuzz` / `make fuzz-seed2` | **502 / 502, 0 divergences** |

All green. Later phases regress against these commands; behavior-preserving tickets (DRY-407/408/409)
must keep the fuzzer byte-identical to this baseline.
