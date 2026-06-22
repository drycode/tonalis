"""A real (anchored) iReal chord-token validator — NOT the permissive CST span scanner.

The CST ``_chord`` accepts ``Cxyzzy`` and shreds ``Cgarbage`` into Chord+Repeat tokens; this
grammar validates the whole token end-to-end. Build-time gate (test): it accepts every distinct
chord token in the 3100-chart corpus and rejects the typo set.
"""

import re

_QUALITY = r"(?:-|\^|o|h|\+|sus)?"  # optional primary quality
# one extension/alteration unit: degree (opt accidental), major-extension ^N, sus/alt/add,
# or a bare quality glyph. Repeatable (e.g. 7b9#11, 69).
# NOTE: `add[0-9]+` uses an EXPLICIT ASCII digit class, NOT `\d`. Python's `\d` is Unicode-aware
# (it matches `٣`/`３`), but the polyglot contract is ASCII-only digits (SPEC.md §1.1/§5.1), and
# the TS/Rust ports are ASCII-only — so `Cadd٣`/`Cadd²` must be `bad-chord` here too.
_EXT = r"(?:[b#]?(?:5|6|9|11|13)|\^(?:7|9|11|13)?|sus|alt|add[0-9]+|o|h|\+|2|4|7)"
_CHORD = re.compile(
    r"^[A-G][b#]?"  # root
    rf"{_QUALITY}"
    rf"(?:{_EXT})*"  # extensions / alterations
    r"(?:/[A-G][b#]?)?$"  # optional slash bass
)
_SLASH_BASS = re.compile(
    r"^/[A-G][b#]?$"
)  # standalone bass continuation (e.g. W/A -> /A)


def is_valid_chord(token: str) -> bool:
    """True iff the token is a well-formed iReal chord (or a no-chord / bass marker)."""
    if token in ("N.C.", "n"):
        return True
    if not token:
        return False
    t = token.replace("*", "")  # tolerate the augmented layout-star artifact (Bb*7+*)
    return bool(_CHORD.match(t)) or bool(_SLASH_BASS.match(t))
