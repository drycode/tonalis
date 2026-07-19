# music-dsl

Pure music-theory domain library: notes, intervals, scale degrees, chord
qualities, scales, and chord encoding. Zero runtime dependencies. This is the
Python reference implementation; TypeScript (`@tonalis/music-dsl` on npm) and
Rust (`tonalis-music-dsl` on crates.io) ports conform to the same spec and a shared
429-case conformance suite plus a seeded three-way differential fuzzer.

`music-dsl` is the theory core underneath [`tonalis`](https://pypi.org/project/tonalis/),
the format-agnostic lead-sheet DSL, and is fully usable on its own.

## Install

```bash
pip install tonalis-music-dsl
```

## Use

```python
from music_dsl import Key, Notes, Scales

key = Key(Notes.Bb, Scales.Major)

# deeper theory lives in submodules
from music_dsl.domain.chords.chord import Chord

chord = Chord("C7")        # raises InvalidChordStringException on bad input
print(chord.encoding)      # canonical numeric chord encoding
```

The import name is `music_dsl` (underscore); the distribution name is
`tonalis-music-dsl`.

## Links

- Source, spec, and conformance suite: <https://github.com/drycode/tonalis>
- License: MIT
