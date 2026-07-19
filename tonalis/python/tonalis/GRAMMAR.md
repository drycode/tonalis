# Tonalis DSL v1 — Grammar Reference

Emit a chart in this DSL. Output **only** the DSL, nothing else.

## Header (required keys: title, key, time)

```
title: All The Things You Are
composer: Jerome Kern
style: Medium Swing
key: Ab
time: 4/4
```

Rules: one `key: value` per line; **no `=` in any value**; `time` is `n/d`.

## Sections and measures

Sections are `[A]`, `[B]`, `[C]`, `[D]`, `[Intro]`/`[i]`, `[Verse]`/`[v]`.
Measures are separated by `|`. Chords inside a measure split the bar evenly;
add `:N` for an explicit beat count.

```
[A]
| F-7 | Bb7 | Eb^7 | Ab^7 |
| D-7 G7 | C^7 | C^7 | C^7 |
```

## Repeats, endings, navigation

`{ ... }` is a repeat; `1.`/`2.` mark first/second endings; `@segno`, `@coda`,
`[time: 3/4]` mid-chart, and `<staff text>` are supported. `@break` (or
`@newline`) on its own line forces the next section/measure onto a new line
(a vertical-space / line-break layout hint); use it for layout, e.g. to put an intro on its own row.

Layout model: iReal displays a fixed **4-cell bar** regardless of meter (the
time signature affects playback only) and auto-wraps every **4 bars per row**.
So rows come out clean by default; emit `@break` only where a section must
start on a fresh row after a short tail (e.g. a 2-bar second ending). Bars
holding 4+ chords render wider than the grid — unavoidable in v1.
For a D.S./D.C. al Coda: `@segno` marks the jump-back point, `@tocoda` (placed
*after* a measure) marks the "To Coda" jump-from, and `@coda` marks the coda
section (the destination). `@fine` marks the Fine (end) point for a D.C./D.S. al Fine.

```
[Intro]
| D-7 | G7 |
@break
[A]
{ | C^7 | A-7 | 1. D-7 | G7 | }
| 2. D-7 | G7 |
```

## Chord vocabulary

Quality: `-` minor, `^` major-7, `o` dim, `h` half-dim, `+` aug, `sus`.
Extensions: `b5 #5 6 b9 9 #9 11 #11 b13 13`. No-chord: `N.C.`.

The following are all VALID chord tokens (the drift gate asserts each passes
the parser's `is_valid_chord`):

<!-- valid-chords -->
```
C
C^7
A-7
G7
D-7
F^7
Bbo7
Eh7
C+
Csus
C7b9
G7#5
F#-7b5
Ab^7
C/E
N.C.
```
<!-- /valid-chords -->

## Banned constructs

The following DSL snippets MUST fail to compile (the drift gate asserts each
yields an error finding):

<!-- banned-dsl -->
```
title: Has = Sign
key: C
time: 4/4

[A]
| C |
---
title: Bad Section
key: C
time: 4/4

[Z]
| C |
---
title: Bad Time
key: C
time: 9
---
title: Bad Chord
key: C
time: 4/4

[A]
| Zxq9 |
```
<!-- /banned-dsl -->

Each banned snippet above is separated by a line containing only `---`.
