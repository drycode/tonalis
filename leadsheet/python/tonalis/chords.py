"""Chord-token validation for the lead-sheet linter, standing on MusicDSL.

Replaces ``chord_grammar``'s hand-rolled regex: the "is this a real chord" decision is
delegated to MusicDSL's ``Chord()`` (the theory library is the single source of truth for
what a chord is). The handful of non-chord lead-sheet tokens that ``Chord()`` rightly
rejects but the linter must still accept are preserved here verbatim:

  * ``N.C.`` / ``n`` — explicit no-chord markers.
  * a standalone slash-bass continuation (``/A``) — a bass note carried over from the
    previous chord, with no quality of its own.
  * the augmented layout-star artifact (``Bb*7+*``) — lead-sheet notation sometimes glues a
    ``*`` to a chord as a layout marker; strip it before validating.

This module may import ``music_dsl`` (the theory lib tonalis stands on) per the Phase 1
one-way dependency rule (leadsheet -> music_dsl); ``music_dsl`` must never import tonalis.
"""

import re

from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
from music_dsl.domain.chords.chord import Chord

_SLASH_BASS = re.compile(r"^/[A-G][b#]?$")  # standalone bass continuation, e.g. /A


def is_valid_chord(token: str) -> bool:
    """True iff the token is a well-formed chord OR a no-chord / bass marker."""
    if token in ("N.C.", "n"):
        return True
    if not token:
        return False
    t = token.replace("*", "")  # tolerate the augmented layout-star artifact (Bb*7+*)
    if _SLASH_BASS.match(t):
        return True
    try:
        Chord(t)
        return True
    except InvalidChordStringException:
        return False
