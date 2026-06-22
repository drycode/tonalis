/**
 * The real (anchored) iReal chord-token validator (SPEC.md §5 — the regex is authoritative).
 *
 * Transcribed VERBATIM from the normative reference regexes in SPEC.md §5.1 (which match
 * `SCRUBBED/dsl/chord_grammar.py`). Where prose and regex disagree, the REGEX wins.
 */

// _QUALITY    = (?:-|\^|o|h|\+|sus)?
const _QUALITY = "(?:-|\\^|o|h|\\+|sus)?";

// _EXT = (?:[b#]?(?:5|6|9|11|13)|\^(?:7|9|11|13)?|sus|alt|add[0-9]+|o|h|\+|2|4|7)
// ASCII digits only (SPEC.md §1.1/§5.1): `add[0-9]+`, not `\d`, so `Cadd٣`/`Cadd²` are bad-chord.
const _EXT = "(?:[b#]?(?:5|6|9|11|13)|\\^(?:7|9|11|13)?|sus|alt|add[0-9]+|o|h|\\+|2|4|7)";

// _CHORD      = ^[A-G][b#]? _QUALITY (?: _EXT )* (?:/[A-G][b#]?)?$
const _CHORD = new RegExp(`^[A-G][b#]?${_QUALITY}(?:${_EXT})*(?:/[A-G][b#]?)?$`);

// _SLASH_BASS = ^/[A-G][b#]?$
const _SLASH_BASS = /^\/[A-G][b#]?$/;

/**
 * True iff the token is a well-formed iReal chord (or a no-chord / bass marker).
 *
 * Mirrors `is_valid_chord`: `N.C.` and `n` are valid; empty is invalid; the layout-star
 * artifact `*` is stripped before matching.
 */
export function isValidChord(token: string): boolean {
  if (token === "N.C." || token === "n") return true;
  if (!token) return false;
  const t = token.replace(/\*/g, ""); // tolerate the augmented layout-star artifact (Bb*7+*)
  return _CHORD.test(t) || _SLASH_BASS.test(t);
}
