# Lead-Sheet Language — Normative Specification (v1, leadsheet)

**Status:** NORMATIVE. This is the executable-spec contract for the **pure lead-sheet / chord-chart
language** (`leadsheet`: Python reference + TypeScript + Rust ports). It is **format-agnostic**: it
covers the language (lexical structure, document/header/body semantics, the chord grammar, the
canonical AST, and the findings codes) and produces **no vendor file/URL format**. Rendering the AST
into any specific notation-app format (field layout, glyph mapping, target-specific beat rendering)
is the job of a separate downstream codec built on top of this core, and is out of scope here.

The conformance suite under `conformance/tonalis/cases/` is the machine-checkable form of this
document; where this prose and the suite disagree on a *blessed* value, the suite (generated from
the Python reference) is the bug report — but no case may be blessed for behavior this document does
not describe (see §0.2 Anti-circularity).

A conformant `leadsheet` implementation reads DSL **text** and produces (a) a canonical **AST**
(`LeadSheet`, §2.1) and (b) a list of **findings** (errors + warnings). The AST and findings are the
conformance artifacts here (§0.1); any downstream vendor-format rendering is out of scope and is
asserted separately by its own codec suite, if any.

Reference implementation: `tonalis/python/tonalis/` (`parser.py → ast.py → lint.py`, with
`serialize.py` for the AST↔JSON projection and `serialize_text.py` for the AST→text printer).

---

## 0. Conformance model

### 0.1 Assertion hierarchy

A `leadsheet` conformance case is `{name, tags[], dsl, expect:{ast?, findings?, text?}}`. An
implementation is conformant on a case iff:

- **`ast` — OPTIONAL, structural.** When present, the canonical `LeadSheet` JSON (§2.1) MUST be
  **deep-equal** to `expect.ast`. Not every case carries an `ast`.
- **`text` — OPTIONAL, golden.** When present (it rides along with `ast`), `serialize(ir)` MUST
  equal `expect.text` exactly, and `parse(serialize(ir))` MUST equal `ir` modulo `line` (§2.1).
- **`findings` — compared on `(code, severity, line)` only**, order-independent. **Message text
  is non-normative** (informational, may differ between ports). A case with an `error` finding
  asserts compilation **fails**; a warning-only case asserts compilation **succeeds** with those
  warnings present.

Every `leadsheet` case asserts `ast` OR `findings` (or both) — there is no URL artifact here.

### 0.2 Anti-circularity

`expect` values are generated from the Python reference and blessed once. That makes the suite
assert the reference's behavior — acceptable **only** because every behavior the suite locks is
described by THIS document. The bless tool (which generates `expect` values; it is a development
tool, not shipped with this library) enforces this **mechanically for finding-code membership
only**: it **fails** if a case emits a finding `code` that the §7 findings-code table does not
document. It does **not** (and cannot) prove the full AST byte-values are derivable from prose —
that obligation is on the human reviewer at bless time: amend the spec to freeze any new quirk, or
fix the implementation, **before** blessing.

### 0.3 Total parsing

The parser/linter **never throws** on arbitrary input; malformed input becomes findings. The
public surface is `parse_dsl(text) -> {chart?, findings}` plus `lint(chart) -> [finding]`. An
unexpected internal exception SHOULD NOT occur for any input within the size caps (§1.3).

---

## 1. Lexical structure

### 1.1 Encoding & line endings

- Input is UTF-8 text. A leading UTF-8 BOM (`U+FEFF`) is stripped.
- **Line terminators (NORMATIVE).** Lines are split on exactly **`\r\n`, `\n`, `\r`** (a `\r\n`
  pair counts as one terminator). This is the **only** terminator set; the Unicode "line
  boundaries" that Python's `str.splitlines()` additionally honors (`\v`, `\f`, `\x1c`, `\x1d`,
  `\x1e`, `\x85`, ` `, ` `) are **NOT** terminators here — they are ordinary characters
  within a line. The reference therefore does **not** use `str.splitlines()`; it splits on the
  three-form set above so all ports agree byte-for-byte.
- **Digits are ASCII only (NORMATIVE).** Everywhere this document writes a digit (`DIGIT`, `\d`,
  "decimal digits") it means the ASCII set **`[0-9]`** and nothing else. Non-ASCII digits
  (e.g. Arabic-Indic `٣`, fullwidth `３`, superscript `²`) are **never** digits: a `time` value,
  `[time:]` body directive, `:N` beat count, ending number, or `add\d+` chord extension containing
  one is malformed and emits the site's finding (`bad-time` / `bad-beats` / `bad-chord`), never a
  parsed number. (The reference enforces this with ASCII-only character classes and an ASCII-digit
  predicate — not Python's Unicode-aware `\d` / `str.isdigit()`, which would otherwise accept
  `٣` and even crash on `int('²')`.)
- A line is processed `strip()`-ped of surrounding whitespace except header values, which are
  read literally to end of line (§3.1) and then right-stripped.

### 1.2 Comments & blank lines

- A line whose stripped form is empty, or begins with `#`, is ignored (in both header and body).

### 1.3 Size caps (each violation is an `error`, code `too-big`, and aborts)

| Cap | Value |
|---|---|
| `MAX_BYTES` | 262144 (256 KiB) — total input |
| `MAX_LINES` | 5000 |
| `MAX_LINE_LEN` | 1000 |
| `MAX_MEASURES` | 2000 |
| `MAX_CELLS_PER_MEASURE` | 16 |
| `MAX_CHORD_TOKEN_LEN` | 50 (chord text, excluding any `:N`) |
| `MAX_ALT_CHORD_TOKENS` | 8 (space-separated tokens inside one `(...)` alt group) |

`too-big` from `MAX_BYTES`/`MAX_LINES`/`MAX_LINE_LEN` carries `line=0` (whole-input) except the
per-line length check (`line=n`); `MAX_MEASURES` and `MAX_CELLS_PER_MEASURE` carry the offending
measure's source line.

### 1.4 Numeric value cap (NORMATIVE — `MAX_METER`)

Independent of the size caps, every parsed integer in the DSL is bounded:

| Cap | Value | Applies to |
|---|---|---|
| `MAX_METER` | 64 | a `time` meter numerator **or** denominator (header `time` and mid-body `[time:]`); a `:N` beat count; an `N.` ending number |

The bound is a hard ceiling, not a size limit on text: a number that is well-formed `[0-9]+` but
**exceeds** `MAX_METER` is malformed at that site and emits the site's finding (it never reaches
rendering, so no port can be driven into a multi-gigabyte ` `-padding allocation or a fixed-width
integer overflow). Finding by site:

- a `time` / `[time:]` meter component `> MAX_METER` → **error** `bad-time` (same as a non-matching
  meter, §3.2/§4.4);
- a `:N` beat count `> MAX_METER` → **error** `bad-beats` (§4.2);
- an `N.` ending number `> MAX_METER` → **error** `too-big` (carries the measure's source line; no
  dedicated semantic code, and an ending that large can only be a typo).

---

## 2. Document structure

A document is a **header** (zero or more `key: value` lines) followed by a **body** (sections,
navigation directives, and measure lines). The body begins at the first line whose stripped first
character is `[`, `|`, or `{`, or the first non-`key: value` line.

### 2.1 Canonical AST (the `ast` projection)

The IR is **neutral**: it stores no vendor-format detail. The root is `LeadSheet`; a section carries
a neutral `kind` role (a downstream codec maps it to whatever section marker its target format uses);
a measure carries a `barline` enum (mapped to the target's barline glyphs by the codec) plus an
opaque ordered `hints` list (where `@break`/`@newline` live, with **no** lead-sheet semantics).

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

The `ast` projection **is** the canonical JSON; `schema_version` is `1` at the `LeadSheet` root (the
first key). `from_json` of an unknown **major** version is rejected. Key order for `Section` is
`label, kind, measures`; for `Measure` is `cells, ending, bar_open, barline, nav, hints, line`; for
`Cell` it is `chord, beats, alt` — fixed exactly as written. **`meta` key order is NON-normative**:
an `ast` assertion is compared **deep-equal** (§0.1), so a port may emit `meta` keys in any order —
only the present keys and their values matter (the reference happens to emit them in source-encounter
order). `nav` tuples render as nested arrays; `meta.time` renders as `[num, den]`. `kind` is the
neutral section role (`"a"`…`"d"`, `"intro"`, `"verse"`). `barline` is the neutral right-barline:
`"normal"` (normal/open-`{`-context), `"repeat_end"` (closed by `}`), or `"final"` (closed by `Z` or
`||`). `hints` is an opaque ordered list of render-hints (`"break"` for `@break`/`@newline`)
with **no** lead-sheet semantics; a downstream codec may consume it, a plain-text target ignores it. `beats` is `null`
unless an explicit `:N` was written. `alt` is the raw parenthesized text including the parentheses,
e.g. `"(Db7)"`, or `null`.

The `ast` projection round-trips: `from_json(to_json(ir)) == ir` (lossless, `line` preserved), and
`parse(serialize(ir)) == ir` modulo the `line` source-position artifact (the canonical text printer
re-flows layout). The conformance suite asserts both, plus the canonical `expect.text` golden, on
every ast-bearing case.

### 2.2 Grammar (EBNF, informative — see §5 for chord grammar)

```
document     = header body ;
header       = { blank | comment | meta-line } ;
meta-line    = key ":" value EOL ;
key          = ALPHA { ALPHA } ;
value        = { any-char-except-EOL } ;          (* read literally, then rstrip *)

body         = { blank | comment | time-line | section-line | nav-line | text-line
               | measure-line } ;
time-line    = "[time:" int "/" int "]" EOL ;
section-line = "[" ALPHA { ALPHA } [ DIGIT { DIGIT } ] "]" EOL ;
nav-line     = "@" directive EOL ;                (* segno | coda | tocoda | fine | break/newline *)
text-line    = "<" { any } ">" EOL ;
measure-line = { barline | cell-run } ;           (* one source line -> >=0 Measures *)
barline      = "{" | "}" | "||" | "|" | "Z" ;
cell-run     = [ ending ] cell { WS cell } ;
ending       = DIGIT { DIGIT } "." ;
cell         = chord [ ":" DIGIT { DIGIT } ] [ "(" alt ")" ]   (* inline alt, no space *)
             | "(" alt ")" ;                                    (* alt for preceding chord *)
alt          = chord { WS chord } ;               (* <= MAX_ALT_CHORD_TOKENS *)
```

---

## 3. Header semantics

### 3.1 Recognized keys

`title`, `composer`, `style`, `key`, `time`. Keys are matched case-insensitively against
`^[A-Za-z]+\s*:\s*(.*)$`; the value is read literally to EOL then right-stripped.

- Any other key → **warning** `unknown-key` (the line is otherwise ignored).
- A value containing `=` → **error** `meta-delimiter` (`=` is reserved as a field delimiter by
  common downstream encodings and is banned from metadata). The check runs for every header line,
  including `time`.

### 3.2 `time`

The value must match `^[0-9]+\s*/\s*[0-9]+$` (ASCII digits only, §1.1) **and** both components
must be `≤ MAX_METER` (§1.4). It is stored in `meta` as the tuple `[num, den]`. A non-matching
value, a non-ASCII digit, or a component `> MAX_METER` → **error** `bad-time`. `time` is also the
default meter for beat checks.

### 3.3 Required headers

`title`, `key`, `time` are required. A missing one → **error** `missing-header` (`line=0`).
A present-but-empty `title` → **error** `missing-header` (`line=0`, "title must be non-empty").
`key` and `composer`/`style` MAY be empty.

### 3.4 Duplicate / conflicting headers

A header key is a singleton. Re-stating it:

- with the **same** value → **warning** `duplicate-header`;
- with a **different** value → **error** `conflicting-header`.

In both cases the **first** value is kept.

---

## 4. Body semantics

### 4.1 Sections

`[A]`, `[B]`, `[C]`, `[D]`, `[Intro]`/`[i]`, `[Verse]`/`[v]` are recognized, with an optional
trailing integer (e.g. `[A2]`). The `label` is the name plus that integer (`"A2"`); the `kind` is
the neutral section role:

| Name | kind |
|---|---|
| `A`,`B`,`C`,`D` | `a`,`b`,`c`,`d` |
| `Intro`,`i` | `intro` |
| `Verse`,`v` | `verse` |

A downstream codec generates whatever section marker its target format uses from `(kind, label)`; no
such marker is stored in the IR. An unrecognized section name → **error** `unknown-section`
(`kind` defaults to `a`). If a measure appears before any `[Section]`, an implicit section
`label="A", kind="a"` is opened. A declared section with no measures → **warning** `empty-section`
(`line=0`); it is dropped from the rendered body.

### 4.2 Beats and the `:N` clause (FROZEN v1 NORMATIVE)

A cell may carry an explicit beat count `chord:N` (`N` one-or-more ASCII digits `[0-9]`, §1.1).
A non-digit (including a non-ASCII digit) after `:`, or `N > MAX_METER` (§1.4) → **error**
`bad-beats`.

**Beat-fill rule (linter).** Let `numerator` be the active meter's top number. Explicit beats sum
to `explicit`; the `remainder = numerator - explicit` is split **evenly** across the
*unannotated* cells:

- If there are unannotated cells and (`remainder <= 0` **or** `remainder % count != 0`): the bar
  cannot be filled. For a **non-pickup** measure this is an **error** `beat-sum`. The **first and
  last** measures of the whole chart are pickups (anacrusis): an *under*-full pickup is allowed,
  but an *over*-full bar (`sum(pattern) > numerator`) is **always** `beat-sum` error, pickup or not.
- If all cells are explicit, the bar is well-formed iff `explicit == numerator` (else `beat-sum`,
  with the pickup relaxation as above).
- A well-formed but **uneven** explicit pattern not in the 4/4 allowlist
  `{(2,1,1),(1,1,1,1),(1,1,2),(3,1),(1,3),(2,2)}` → **warning** `beat-unsupported`
  (a downstream codec whose target can't express the uneven split may fall back to even-split
  rendering; the `ast` keeps the real beats regardless).

> The `ast` retains the real `beats` per cell. How `:N` is rendered into any specific target format
> is a downstream **codec** concern, out of scope here. A measure with **more cells than beats can
> fill** (e.g. five unannotated cells in 4/4) is a `beat-sum` **error** here and never reaches
> rendering (§Banned).

### 4.3 Repeats, endings, final bar

- `{` opens a repeat; `}` closes one. Each measure tracks `bar_open` (preceded by `{`) and
  `barline` (`repeat_end` if closed by `}`, else `normal`). A `}` with no open repeat → **error**
  `unbalanced-repeat`. Unclosed `{` at end of chart → **error** `unbalanced-repeat` (`line=0`).
- `N.` ending prefixes (`1.`, `2.`, …) set `Measure.ending`. An ending in a section that has **no**
  `bar_open` measure → **error** `ending-without-repeat`. **Line heuristic (PINNED):** the finding's
  `line` is the source line of the **first** measure in that section that bears an ending.
- `Z` or `||` set `barline="final"` (final barline). A `Z`/`||` that is **not** on the last measure
  of the chart → **warning** `mid-final-bar`.
- **Empty buffers DROP, they do not become measures.** A barline-delimited segment whose content
  is blank (`| |`, or trailing/leading whitespace between bars) is **skipped** by the parser — it
  produces **no** `Measure` and **no** finding. So `| C6 |  | D7 |` yields exactly two measures
  (`C6`, `D7`), the empty middle silently dropped.
- A `Measure` with **zero cells** → **warning** `empty-measure`. This can only arise when a measure
  is created for a reason *other* than a chord — i.e. it carries an **ending prefix** (`1.` with no
  chord after it) or an **alt group with no preceding chord** (`(Db7)` standing alone, which also
  emits `alt-without-chord`).

### 4.4 Navigation directives

Navigation lines (`@…`, `<…>`, `[time:…]`) accumulate as **pending** nav and attach to the **next**
measure — with one exception (`@tocoda`, below). Order within a measure's `nav` is: pending nav (in
source order) first, then any measure-attached nav.

- `@segno` → nav `["segno"]`.
- `@coda` → nav `["coda"]` (marks the coda destination, before the chord).
- `@tocoda` / `@to coda` / `@to-coda` → the "To Coda" jump-point: appends `["tocoda"]` to the
  **PRECEDING** measure's nav, NOT the next measure. Checked before `coda` because the word `tocoda`
  contains `coda`. If there is no preceding measure → **warning** `tocoda-without-measure`.
- `@fine` → nav `["fine"]` (the Fine/end point for a D.C./D.S. al Fine). It attaches to the next
  measure like other pending nav. How a downstream codec renders `fine` (or substitutes a glyph when
  its target format has no distinct Fine marker) is out of scope here.
- `@break` / `@newline` → appends `"break"` to the **next** measure's `hints` (an opaque render-hint
  — a downstream codec may map it to a layout/line-break directive in its target format) with **no**
  lead-sheet semantics. It is **NOT** a `nav` item; a plain-text target ignores it.
- Any other `@directive` → **warning** `unknown-nav`.
- `<text>` (a line beginning `<` and ending `>`) → nav `["text", "<...>"]`.
- `[time: n/d]` mid-body → nav `["time", [n, d]]` (`n`, `d` ASCII digits `[0-9]`, each `≤ MAX_METER`,
  §1.1/§1.4). If `n/d` equals the currently active meter → **warning** `redundant-time`. The new
  meter governs subsequent beat checks and cell padding. A `[time: n/d]`-shaped line whose components
  are well-formed ASCII digits but exceed `MAX_METER` → **error** `bad-time` (the directive is
  recognized but the meter is rejected; it contributes no nav). A non-ASCII digit makes the line not
  match the `[time:…]` shape at all; it then falls through to ordinary parsing.

### 4.5 Coda / segno count

- More than 2 `@coda` points → **error** `coda-count` (more than two coda points cannot be flattened
  into a single linear playback order).
- Exactly 2 `@coda` with **no** `@segno` → **warning** `coda-needs-segno` (plays D.C., not D.S.).

---

## 5. Chord grammar (NORMATIVE — music_dsl parser is authoritative)

The chord token grammar is defined by `is_valid_chord` (in `chords.py`, which delegates to the
`music_dsl` `Chord` parser). It accepts **more** than a fixed 10-extension list. **The regex below
is the normative description of the grammar; the `music_dsl` parser is the executable validator and
is authoritative where the two could disagree** (see the Phase-3 note in §5.1). A port built to a
prose subset fails the goldens on day one.

### 5.1 The validator (normative pseudocode)

```
is_valid_chord(token):
    if token in {"N.C.", "n"}: return true       # no-chord markers
    if token is empty: return false
    t = token with every "*" removed             # tolerate the layout-star artifact, e.g. "Bb*7+*"
    return CHORD.fullmatch(t) or SLASH_BASS.fullmatch(t)

# anchored, full-token:
ROOT       = [A-G] [b#]?
QUALITY    = ( - | ^ | o | h | + | sus )?          # optional, at most one
EXT_UNIT   = [b#]? (5|6|9|11|13)                    # degree with optional accidental
           | \^ (7|9|11|13)?                        # major-extension glyph, bare ^ allowed
           | sus | alt | add[0-9]+                  # words; add requires >=1 ASCII digit
           | o | h | +                              # quality glyphs reused as extensions
           | 2 | 4 | 7                              # bare degrees 2/4/7
SLASH_BASS = / [A-G] [b#]?                          # bass note

CHORD      = ^ ROOT QUALITY ( EXT_UNIT )* ( / [A-G] [b#]? )? $
SLASH_ONLY = ^ / [A-G] [b#]? $                      # a standalone bass continuation, e.g. "/A"
```

Exact reference regexes (the literal `re` patterns). **`\d` here means ASCII `[0-9]` only** (§1.1):
the only `\d` is in `add\d+`, so `Cadd٣` (Arabic-Indic) / `Cadd²` (superscript) are **invalid**
(`bad-chord`). The reference compiles `add\d+` with `re.ASCII` (or the explicit class `add[0-9]+`)
so it agrees with the ASCII-only TS/Rust ports.

```
_QUALITY    = (?:-|\^|o|h|\+|sus)?
_EXT        = (?:[b#]?(?:5|6|9|11|13)|\^(?:7|9|11|13)?|sus|alt|add[0-9]+|o|h|\+|2|4|7)
_CHORD      = ^[A-G][b#]?(?:-|\^|o|h|\+|sus)?(?:(?:[b#]?(?:5|6|9|11|13)|\^(?:7|9|11|13)?|sus|alt|add[0-9]+|o|h|\+|2|4|7))*(?:/[A-G][b#]?)?$
_SLASH_BASS = ^/[A-G][b#]?$
```

> **Note (Phase 3):** The regex above is the normative *description* of the chord grammar, but it is
> no longer the executable validator. All three reference ports delegate `isValidChord` to the
> `music_dsl` `Chord` parser (the executable source of truth); where the regex and the parser could
> disagree, the parser is authoritative. A frozen 952-token reconciliation oracle
> (`tonalis/fixtures/chord_oracle.json`) pins their agreement, modulo one blessed token (`C7777`,
> which the old regex wrongly accepted and `music_dsl` correctly rejects).

### 5.2 Consequences (verified accepted)

- Bare degrees: `C2`, `C4`, `C5`, `C7`. (`3` and `1` are NOT bare-degree units; there is no bare
  `C3`/`C1`. They are only reachable as the **`add\d+`** EXT unit — see below — so `Cadd3`/`Cadd1`
  are valid whole chords, but `add3` is an extension on a root, never a standalone chord by itself.)
- Major extensions: `C^` (bare), `C^7`, `C^9`, `C^11`, `C^13`.
- `add\d+` EXT unit: the unit is `add` immediately followed by `≥ 1` ASCII digit, e.g. the chords
  `Cadd9`, `Cadd3`, `C7susadd3`. `Cadd` alone (no digit) is **invalid**; `add\d+` is an EXT applied
  to a `ROOT` (+ optional `QUALITY`), so it composes like any other extension and is never a chord on
  its own.
- Combined-degree shorthand `69`: `C69` (= `6` then `9`).
- Quality glyphs reused as extensions: `Co7`, `Ch7`, `C7+`, `Co^7` (the leading quality is optional
  so `o`/`h`/`+` may also recur as EXT units).
- `alt`: `C7alt`, `Calt`.
- Slash bass: `D-/C`, and the standalone continuation `/A` (but `W/A` is invalid — `W` is not a root).
- The grammar is **permissive by design**: pathological-but-valid repeats such as `C7777` and
  `Csussus` are ACCEPTED (the EXT unit is `*`-repeatable). A faithful port-of-the-regex agrees.
- Rejected typos: `Cxyzzy`, `Cgarbage`, `C!!!`, `Cthe`, `Czzzz`, `Hello`, `""`. Note also that the
  spelled-out words `maj`/`min`/`dim`/`aug` are **rejected** (`Cmaj7`, `Cmin7` are NOT valid — only
  the glyph forms `C^7`, `C-7`, `Co7`, `C+` are).

### 5.3 Where chord validity is checked

The linter calls `is_valid_chord` on every cell's `chord` (non-empty) and on every space-separated
token inside an `alt` group; either failing → **error** `bad-chord`. `N.C.` and `n` are valid
(no-chord). The parser bounds chord token length to `MAX_CHORD_TOKEN_LEN` (§1.3, `token-too-long`).

**Empty-chord cell (FROZEN v1 NORMATIVE).** The chord-validity guard is gated on a **non-empty**
chord (the reference: `if c.chord and not is_valid_chord(...)`). A cell with an **empty chord token**
— e.g. a bare beat count `:N` with no chord glyph before the colon, which parses to
`Cell(chord="", beats=N)` — therefore **skips** the `bad-chord` check entirely. Such a cell is
**legal**: it is **not** a `bad-chord`, the chart compiles, and emits **no** finding for the empty
chord. This is distinct from a **cell-less** measure (zero cells, §4.3), which warns `empty-measure`;
an empty-chord cell is a real cell (it still carries `beats`/`alt`).

---

## 7. Findings code table

| code | severity | line | meaning |
|---|---|---|---|
| `too-big` | error | 0 or n | a size cap (§1.3) was exceeded, or an ending number `> MAX_METER` (§1.4) |
| `missing-header` | error | 0 | a required header is missing or `title` empty (§3.3) |
| `unknown-key` | warning | n | unrecognized header key (§3.1) |
| `meta-delimiter` | error | n | `=` in a metadata value (§3.1) |
| `bad-time` | error | n | malformed `time` value, non-ASCII digit, or meter component `> MAX_METER` (§3.2/§4.4/§1.4) |
| `duplicate-header` | warning | n | header restated with same value (§3.4) |
| `conflicting-header` | error | n | header restated with different value (§3.4) |
| `unknown-section` | error | n | unrecognized `[Section]` name (§4.1) |
| `empty-section` | warning | 0 | declared section with no measures (§4.1) |
| `empty-chart` | error | 0 | no sections or measures |
| `bad-beats` | error | n | non-(ASCII-)digit after `:` in a cell, or `:N` count `> MAX_METER` (§4.2/§1.4) |
| `beat-sum` | error | n | measure under/overflows its meter (non-pickup) (§4.2) |
| `beat-unsupported` | warning | n | uneven explicit layout off the allowlist (§4.2) |
| `unbalanced-repeat` | error | n or 0 | `}` with no `{`, or unclosed `{` at EOF (§4.3) |
| `ending-without-repeat` | error | n | nth ending in a section with no repeat (§4.3) |
| `mid-final-bar` | warning | n | `Z`/`||` not on the last measure (§4.3) |
| `empty-measure` | warning | n | a cell-less measure (ending-only / stray-alt) (§4.3) |
| `tocoda-without-measure` | warning | n | `@tocoda` with no preceding measure (§4.4) |
| `unknown-nav` | warning | n | unrecognized `@directive` (§4.4) |
| `redundant-time` | warning | n | `[time:]` repeats the current meter (§4.4) |
| `coda-count` | error | 0 | more than 2 `@coda` points (§4.5) |
| `coda-needs-segno` | warning | 0 | 2 codas, no segno (§4.5) |
| `bad-chord` | error | n | invalid chord or alt token (§5.3) |
| `token-too-long` | error | n | chord token exceeds `MAX_CHORD_TOKEN_LEN` (§1.3) |
| `alt-too-long` | error | n | alt group exceeds `MAX_ALT_CHORD_TOKENS` (§1.3) |
| `alt-without-chord` | warning | n | `(alt)` group with no preceding chord |

**Line conventions (PINNED).** Chart-wide findings carry `line=0`: `missing-header`, `empty-chart`,
`unbalanced-repeat` (the unclosed-`{` form), `empty-section`, `coda-count`, `coda-needs-segno`, the
input-wide `too-big`. `ending-without-repeat` uses the first ending-bearing measure's line (§4.3).
All other measure/header findings carry their source line.

---

## 8. Banned constructs (each asserts a specific error `code`)

A "banned" conformance case carries DSL that MUST fail with the listed `code`:
`bad-chord`, `bad-time`, `meta-delimiter`, `missing-header`, `conflicting-header`, `unknown-section`,
`beat-sum`, `bad-beats`, `unbalanced-repeat`, `ending-without-repeat`, `coda-count`, `empty-chart`,
`too-big`, `token-too-long`, `alt-too-long`. Warning-only constructs (`mid-final-bar`,
`empty-measure`, `redundant-time`, `duplicate-header`, `unknown-key`, `unknown-nav`,
`tocoda-without-measure`, `empty-section`, `coda-needs-segno`, `beat-unsupported`,
`alt-without-chord`) compile **successfully** and assert the warning's presence.
