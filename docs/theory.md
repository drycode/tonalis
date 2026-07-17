# The theory model

The `music_dsl` package is the theory core the lead-sheet language sits on. It
models notes, intervals, chords, key-relative chords, scale degrees, and scales.
This page describes the model; the [scale catalog](scales.md) covers scales in
full, and the [API reference](api.md) has the generated per-symbol docs.

## Notes and intervals

`Notes` is an enum of the twelve pitch classes, carrying both sharp and flat
spellings (`C#` and `Db` are distinct members but compare **enharmonically
equal**). `.to_flat()` / `.normalized()` collapse a sharp spelling to its flat
equivalent, which is the canonical form the rest of the model works in (there are
no double accidentals).

`Intervals` names the interval qualities/sizes; interval arithmetic is exposed
through helpers like `semitones_apart_ascending` and, on the realization side,
`interval_pitches`.

## Chords

`Chord` parses a chord token (e.g. `"D-7"`, `"Ab^7"`, `"C7alt"`, `"D-/C"`) into a
structured value with a `root` (a `Notes`) and a bit-packed **encoding**. The
encoding is what membership and diatonicity queries operate on. A chord is
decomposed into:

- **`Triad`** — the triad quality,
- **`Seventh`** — the seventh, and
- **`Extensions`** — an ordered set of extension degrees,

plus a **`HarmonicFunction`** derived from quality alone (the bare
`Chord.harmonic_function` is decided from quality; `harmonic_function_in_key`
sharpens it against a key).

`Chord` is the executable definition of chord validity: the lead-sheet layer's
`is_valid_chord` delegates to this parser. The grammar is permissive by design —
see the [DSL page](dsl.md) for the accepted/rejected token catalog.

## Numeric (key-relative) chords

`NumericChord` is a chord expressed **relative to a key** rather than at an
absolute pitch — its root is a `ScaleDegree` (a roman numeral) instead of a
`Notes`. This is the key-independent form: the same `NumericChord` realizes to
different absolute chords in different keys.

- `chord_in_key(numeric, key_root)` realizes a `NumericChord` into a playable
  absolute `Chord` by pitch class (flat-spelled; slash chords resolve
  recursively against major parents).
- `numeric_from_chord` / `parse_numeric` go the other direction.

## Scale degrees

`ScaleDegree` is an enum of roman-numeral degrees (`I`, `ii`, `bIII`, `#IV`, …),
carrying both major (uppercase) and minor (lowercase) spellings and both
sharp/flat enharmonic spellings, with the inverse maps derived so the two
directions cannot drift. Scale degrees are what `NumericChord` roots are built
from, and what harmonic-function analysis reports against.

## Keys, scales, and realization

A `Key` is a `(root, scale)` pair. Scales are modeled as bit-masks (see the
[scale catalog](scales.md) for the representation and the full 37-scale set).
Two families of query sit on top:

- **Membership** — `contains(scale, pitch_class)` is defined for **every** scale.
- **Function** — `is_diatonic` and `harmonic_function_in_key` are defined **only**
  for scales with a tonal hierarchy, and **refuse** on symmetric/atonal scales.
  This is the two-tier model, covered in depth on the [scale page](scales.md).

The realization layer turns abstract theory into concrete pitches and
frequencies: `note_to_midi`, `midi_to_hz`, `note_to_hz`, `interval_pitches`,
`chord_pitches`, `scale_pitches`, and `scale_degree_pitch`.

## Cross-port surface

The same model is implemented in all three ports. Names differ only by each
language's idiom:

| Concept | Python | TypeScript | Rust |
|---------|--------|-----------|------|
| Chord parse | `Chord` / `parse_chord` | `parseChord` / `ChordModel` | `parse_chord` / `ChordModel` |
| Diatonic query | `is_diatonic` | `isDiatonic` | `is_diatonic` |
| Harmonic function in key | `harmonic_function_in_key` | `harmonicFunctionInKey` | `harmonic_function_in_key` |
| Scale catalog | `Scales` | `Scales` | `Scales` |

Identical scale masks across ports guarantee identical membership and
diatonicity results — which the differential fuzzer verifies over the whole scale
surface.
