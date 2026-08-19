# music-dsl

Pure music-theory domain library: notes, intervals, scale degrees, chord
qualities, scales, and chord encoding. No runtime dependencies. Port of the
Python `music-dsl` reference implementation — all three ports (Python /
TypeScript / Rust) conform to the same spec via a shared 433-case conformance
suite plus a seeded three-way differential fuzzer.

The crate is named `tonalis-music-dsl`; the library target (import path) is
`music_dsl`. It is the theory core underneath the
[`tonalis`](https://crates.io/crates/tonalis) lead-sheet DSL crate and is fully
usable on its own.

## Install

```bash
cargo add tonalis-music-dsl
```

## Use

```rust
use music_dsl::chord::parse_chord;

let chord = parse_chord("C7")?;
```

## Links

- Source, spec, and conformance suite: <https://github.com/drycode/tonalis>
- License: MIT
