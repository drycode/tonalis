"""Frozen reconciliation: the MusicDSL-backed validator must agree with the retired
``chord_grammar`` regex over the whole corpus — except a tiny, explicitly-blessed set.

``fixtures/chord_oracle.json`` records the OLD ``chord_grammar.is_valid_chord`` verdict for
every distinct chord token in the dsl-core conformance corpus (built once by
``tonalis.tools.build_chord_oracle``; CI consumes the frozen fixture only). This test asserts
the NEW ``tonalis.chords.is_valid_chord`` returns the same verdict for every token, so the
swap in Task 4 cannot silently change which tokens the linter accepts.

``_BLESSED`` is the deliberate-difference set: tokens where the new verdict differs from the
frozen OLD verdict by an explicit decision. The single blessed token is one the OLD regex
WRONGLY accepted; MusicDSL (correctly) rejects it, so the new, stricter verdict is the right
one — the oracle just records the old (wrong) ``true``, hence the bless.

  * ``C7777``   — a repeated-digit run; not a real extension.

The iReal ``X4`` sus shorthand (``C4``, ``A4/C`` …) and the ``X7+`` raised-5th form (``C7+``,
``Bb*7+*`` -> ``Bb7+`` == ``Bb7#5``) are NOT blessed: MusicDSL was taught both (sus shorthand
in Task 3, ``7+`` in Task 4), so those tokens now validate and agree with the old grammar
(true == true). ``C7+`` and ``Bb*7+*`` were previously blessed (when MusicDSL rejected ``7+``);
teaching ``7+`` retired them from the bless set, leaving only the genuinely-malformed ``C7777``.
"""

import json
from pathlib import Path

from tonalis.chords import is_valid_chord

_ORACLE = json.loads(
    (Path(__file__).parent / "fixtures" / "chord_oracle.json").read_text(encoding="utf-8")
)

# Tokens where new != old by an explicit decision (see this module's docstring).
_BLESSED = {"C7777"}


def test_new_validator_matches_frozen_oracle():
    mismatches = [
        t for t, old in _ORACLE.items() if is_valid_chord(t) != old and t not in _BLESSED
    ]
    assert not mismatches, f"{len(mismatches)} drift from oracle: {mismatches[:20]}"


def test_blessed_differences_are_real_and_minimal():
    """Every blessed token MUST actually be a live old=true / new=false difference — a stale
    bless (a token that no longer diverges, or isn't in the oracle) is a maintenance hazard."""
    stale = []
    for t in _BLESSED:
        if t not in _ORACLE:
            stale.append(f"{t!r}: not in oracle")
        elif not (_ORACLE[t] is True and is_valid_chord(t) is False):
            stale.append(f"{t!r}: not a live old=true/new=false divergence")
    assert not stale, "stale / wrong blesses: " + "; ".join(stale)


def test_oracle_is_nonempty_and_clean():
    """Guard against an empty/garbage oracle: it must hold a substantial corpus of
    chord-looking tokens only (no iReal control junk)."""
    import re

    assert len(_ORACLE) > 500, f"oracle suspiciously small: {len(_ORACLE)} tokens"
    chordish = re.compile(r"^(?:[A-G][b#]?.*|/[A-G][b#]?|N\.C\.|n)$")
    junk = [t for t in _ORACLE if not chordish.match(t)]
    assert not junk, f"oracle contains non-chord tokens: {junk[:20]}"
