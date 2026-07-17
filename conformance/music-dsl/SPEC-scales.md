# Scale Catalog & Two-Tier Diatonicity — Normative Specification

This is the cross-port contract for Tonalis scales. The blessed conformance cases under
`conformance/music-dsl/cases/` are authoritative; this document is the human-readable
normative reference every port (Python / TypeScript / Rust) implements to.

## 1. Scale representation

A scale is a 12-bit pitch-class set (bit `11-pc` set means the pitch class `pc` semitones
above the tonic is in the scale), repeated **3×** into a 36-bit mask. The triple copy lets
the modal-alignment scan rotate the scale to any root without the sliding window falling
off the most-significant end. `scale_value(name)` returns this mask and is the core contract
— identical masks across ports guarantee identical membership.

Each scale carries a **descriptor**: `mask`, canonical `name`, `category`, and
`supports_diatonic_function` (the two-tier flag).

## 2. The two-tier model (NORMATIVE)

- **Tier 1 — membership.** `contains(scale, pitch_class)` is defined for **every** scale,
  functional or not. It returns whether `pitch_class % 12` (semitones above the tonic) is
  in the scale. Algorithm: take the leading 12-bit copy of the mask; the pitch class `pc`
  is present iff bit `(11 - (pc % 12))` is set.
- **Tier 2 — function.** `is_diatonic` (and any harmonic-function query) is defined **only**
  on scales with `supports_diatonic_function = true`. On a non-functional scale it MUST
  refuse — idiomatically per language: **Python raises**, **TypeScript throws**, **Rust
  returns `Err`** — never a value. A functional query against a non-functional scale that
  returns a value is a conformance failure (see the `refuse-*` cases).

Non-functional scales are the symmetric/atonal set (§3). Everything else is functional.

## 3. The catalog (pitch classes = semitones above the tonic)

### Functional scales

| Name | Category | Pitch classes |
|------|----------|---------------|
| Major (Ionian) | major-mode | 0 2 4 5 7 9 11 |
| Dorian | major-mode | 0 2 3 5 7 9 10 |
| Phrygian | major-mode | 0 1 3 5 7 8 10 |
| Lydian | major-mode | 0 2 4 6 7 9 11 |
| Mixolydian | major-mode | 0 2 4 5 7 9 10 |
| Natural minor (Aeolian) | major-mode | 0 2 3 5 7 8 10 |
| Locrian | major-mode | 0 1 3 5 6 8 10 |
| Melodic minor | melodic-minor | 0 2 3 5 7 9 11 |
| Dorian b2 | melodic-minor | 0 1 3 5 7 9 10 |
| Lydian augmented | melodic-minor | 0 2 4 6 8 9 11 |
| Lydian dominant | melodic-minor | 0 2 4 6 7 9 10 |
| Mixolydian b6 | melodic-minor | 0 2 4 5 7 8 10 |
| Locrian natural 2 | melodic-minor | 0 2 3 5 6 8 10 |
| Altered (Super Locrian) | melodic-minor | 0 1 3 4 6 8 10 |
| Harmonic minor | harmonic-minor | 0 2 3 5 7 8 11 |
| Locrian natural 6 | harmonic-minor | 0 1 3 5 6 9 10 |
| Ionian #5 | harmonic-minor | 0 2 4 5 8 9 11 |
| Dorian #4 (Ukrainian) | harmonic-minor | 0 2 3 6 7 9 10 |
| Phrygian dominant | harmonic-minor | 0 1 4 5 7 8 10 |
| Lydian #2 | harmonic-minor | 0 3 4 6 7 9 11 |
| Ultralocrian | harmonic-minor | 0 1 3 4 6 8 9 |
| Harmonic major | harmonic-major | 0 2 4 5 7 8 11 |
| Double harmonic (Byzantine) | exotic | 0 1 4 5 7 8 11 |
| Hungarian minor | exotic | 0 2 3 6 7 8 11 |
| Hungarian major | exotic | 0 3 4 6 7 9 10 |
| Neapolitan major | exotic | 0 1 3 5 7 9 11 |
| Neapolitan minor | exotic | 0 1 3 5 7 8 11 |
| Major pentatonic | pentatonic | 0 2 4 7 9 |
| Minor pentatonic | pentatonic | 0 3 5 7 10 |
| Blues (minor) | blues | 0 3 5 6 7 10 |
| Bebop dominant | bebop | 0 2 4 5 7 9 10 11 |
| Bebop major | bebop | 0 2 4 5 7 8 9 11 |

The bebop scales are the 7-note parent plus one chromatic passing tone (dominant: the major
7th over Mixolydian; major: the #5 over the major scale).

### Non-functional scales (membership only; functional queries refuse)

| Name | Category | Pitch classes |
|------|----------|---------------|
| Whole tone | symmetric | 0 2 4 6 8 10 |
| Diminished (half-whole) | symmetric | 0 1 3 4 6 7 9 10 |
| Diminished (whole-half) | symmetric | 0 2 3 5 6 8 9 11 |
| Augmented | symmetric | 0 3 4 7 8 11 |
| Chromatic | atonal | 0 1 2 3 4 5 6 7 8 9 10 11 |

## 4. Deferred

**Bebop minor / bebop dorian** is intentionally omitted: the literature carries competing
definitions (Dorian + major-3rd passing tone `0 2 3 4 5 7 9 10` vs Dorian + major-7th
passing tone `0 2 3 5 7 9 10 11`). It will be added once a single definition is chosen, to
avoid blessing a disputed set into the contract.
