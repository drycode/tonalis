# @tonalis/music-dsl

Pure music-theory domain library: notes, intervals, scale degrees, chord
qualities, scales, and chord encoding. Zero runtime dependencies; ships
compiled ESM with type declarations. Port of the Python `music-dsl` reference
implementation — all three ports (Python / TypeScript / Rust) conform to the
same spec via a shared 429-case conformance suite plus a seeded three-way
differential fuzzer.

`@tonalis/music-dsl` is the theory core underneath
[`tonalis`](https://www.npmjs.com/package/tonalis), the format-agnostic
lead-sheet DSL, and is fully usable on its own.

## Install

```bash
npm install @tonalis/music-dsl
```

## Use

```ts
import { parseChord } from "@tonalis/music-dsl";

const chord = parseChord("C7");   // throws InvalidChordStringError on bad input
```

## Links

- Source, spec, and conformance suite: <https://github.com/drycode/tonalis>
- License: MIT
