# Scale catalog & two-tier diatonicity

This is the human-readable form of the cross-port scale contract. The blessed
conformance cases under `conformance/music-dsl/cases/` are authoritative; the
normative source is `conformance/music-dsl/SPEC-scales.md`, and every port
(Python / TypeScript / Rust) implements to it. This page mirrors that spec.

## 1. Scale representation

A scale is a 12-bit pitch-class set (bit `11-pc` set means the pitch class `pc`
semitones above the tonic is in the scale), repeated **3×** into a 36-bit mask.
The triple copy lets the modal-alignment scan rotate the scale to any root
without the sliding window falling off the most-significant end.
`scale_value(name)` returns this mask and is the core contract — identical masks
across ports guarantee identical membership.

Each scale carries a **descriptor**: `mask`, canonical `name`, `category`, and
`supports_diatonic_function` (the two-tier flag).

## 2. The two-tier model (NORMATIVE)

Tonalis separates two questions that are often conflated, because they are not
equally meaningful for every scale.

### Tier 1 — membership

`contains(scale, pitch_class)` is defined for **every** scale, functional or not.
It returns whether `pitch_class % 12` (semitones above the tonic) is in the
scale.

> Algorithm: take the leading 12-bit copy of the mask; the pitch class `pc` is
> present iff bit `(11 - (pc % 12))` is set.

### Tier 2 — function

`is_diatonic` (and any harmonic-function query) is defined **only** on scales with
`supports_diatonic_function = true`. On a non-functional scale it MUST refuse —
idiomatically per language:

| Port | Refusal |
|------|---------|
| Python | **raises** `NonFunctionalScaleError` |
| TypeScript | **throws** |
| Rust | **returns `Err`** |

Never a value. A functional query against a non-functional scale that returns a
value is a conformance failure (the `refuse-*` cases assert this).

### Why two tiers

Diatonic function presupposes a **tonal hierarchy** — a tonic, and degrees that
resolve toward it. The symmetric and atonal scales (whole-tone, the two
diminished scales, augmented, chromatic) have no such hierarchy: every note is
equivalent under the scale's own symmetry, so "is this chord diatonic / what is
its harmonic function" has no meaningful answer. Rather than return an answer
that *looks* authoritative but isn't, those scales refuse the functional query —
while still answering membership, which is always well-defined. Non-functional
scales are exactly the symmetric/atonal set in §3; everything else is functional.

## 3. The catalog

Pitch classes are the semitones above the tonic. **This table is generated from the
live `music_dsl` catalog on every docs build**, so it cannot drift from the code or
the conformance corpus.

<!-- BEGIN GENERATED SCALES -->
*39 scales — generated from the `music_dsl` catalog, so this table cannot drift from the conformance corpus.*

### Functional scales (34)

`contains` **and** `is_diatonic` / harmonic-function queries are defined.

| Scale | Category | Semitones (from tonic) | Diatonic queries |
|-------|----------|------------------------|------------------|
| Major (Ionian) | `major-mode` | 0 2 4 5 7 9 11 | ✅ defined |
| Dorian | `major-mode` | 0 2 3 5 7 9 10 | ✅ defined |
| Phrygian | `major-mode` | 0 1 3 5 7 8 10 | ✅ defined |
| Lydian | `major-mode` | 0 2 4 6 7 9 11 | ✅ defined |
| Mixolydian | `major-mode` | 0 2 4 5 7 9 10 | ✅ defined |
| Natural minor (Aeolian) | `major-mode` | 0 2 3 5 7 8 10 | ✅ defined |
| Locrian | `major-mode` | 0 1 3 5 6 8 10 | ✅ defined |
| Melodic minor | `melodic-minor` | 0 2 3 5 7 9 11 | ✅ defined |
| Dorian b2 | `melodic-minor` | 0 1 3 5 7 9 10 | ✅ defined |
| Lydian augmented | `melodic-minor` | 0 2 4 6 8 9 11 | ✅ defined |
| Lydian dominant | `melodic-minor` | 0 2 4 6 7 9 10 | ✅ defined |
| Mixolydian b6 | `melodic-minor` | 0 2 4 5 7 8 10 | ✅ defined |
| Locrian natural 2 | `melodic-minor` | 0 2 3 5 6 8 10 | ✅ defined |
| Altered (Super Locrian) | `melodic-minor` | 0 1 3 4 6 8 10 | ✅ defined |
| Harmonic minor | `harmonic-minor` | 0 2 3 5 7 8 11 | ✅ defined |
| Locrian natural 6 | `harmonic-minor` | 0 1 3 5 6 9 10 | ✅ defined |
| Ionian #5 | `harmonic-minor` | 0 2 4 5 8 9 11 | ✅ defined |
| Dorian #4 (Ukrainian) | `harmonic-minor` | 0 2 3 6 7 9 10 | ✅ defined |
| Phrygian dominant | `harmonic-minor` | 0 1 4 5 7 8 10 | ✅ defined |
| Lydian #2 | `harmonic-minor` | 0 3 4 6 7 9 11 | ✅ defined |
| Ultralocrian | `harmonic-minor` | 0 1 3 4 6 8 9 | ✅ defined |
| Harmonic major | `harmonic-major` | 0 2 4 5 7 8 11 | ✅ defined |
| Double harmonic (Byzantine) | `exotic` | 0 1 4 5 7 8 11 | ✅ defined |
| Hungarian minor | `exotic` | 0 2 3 6 7 8 11 | ✅ defined |
| Hungarian major | `exotic` | 0 3 4 6 7 9 10 | ✅ defined |
| Neapolitan major | `exotic` | 0 1 3 5 7 9 11 | ✅ defined |
| Neapolitan minor | `exotic` | 0 1 3 5 7 8 11 | ✅ defined |
| Major pentatonic | `pentatonic` | 0 2 4 7 9 | ✅ defined |
| Minor pentatonic | `pentatonic` | 0 3 5 7 10 | ✅ defined |
| Blues (minor) | `blues` | 0 3 5 6 7 10 | ✅ defined |
| Bebop dominant | `bebop` | 0 2 4 5 7 9 10 11 | ✅ defined |
| Bebop major | `bebop` | 0 2 4 5 7 8 9 11 | ✅ defined |
| Bebop Dorian | `bebop` | 0 2 3 4 5 7 9 10 | ✅ defined |
| Bebop minor | `bebop` | 0 2 3 5 7 9 10 11 | ✅ defined |

### Symmetric / atonal scales (5)

Membership (`contains`) works; functional queries **refuse** (Python raises, TS throws, Rust `Err`).

| Scale | Category | Semitones (from tonic) | Diatonic queries |
|-------|----------|------------------------|------------------|
| Whole tone | `symmetric` | 0 2 4 6 8 10 | ⛔ refuses |
| Diminished (half-whole) | `symmetric` | 0 1 3 4 6 7 9 10 | ⛔ refuses |
| Diminished (whole-half) | `symmetric` | 0 2 3 5 6 8 9 11 | ⛔ refuses |
| Augmented | `symmetric` | 0 3 4 7 8 11 | ⛔ refuses |
| Chromatic | `atonal` | 0 1 2 3 4 5 6 7 8 9 10 11 | ⛔ refuses |
<!-- END GENERATED SCALES -->

The bebop scales are the 7-note parent plus one chromatic passing tone (dominant:
the major 7th over Mixolydian; major: the #5 over the major scale).

## 4. Bebop minor — both forms named

"Bebop minor" names two different scales in the literature, so both are in the
catalog under distinct names rather than blessing one as the sole "bebop minor":

- **Bebop Dorian** — Dorian + a natural-3 passing tone (`0 2 3 4 5 7 9 10`), for the ii−7 chord.
- **Bebop minor** — Dorian + a natural-7 passing tone (`0 2 3 5 7 9 10 11`), paralleling the bebop dominant's added-note logic.
