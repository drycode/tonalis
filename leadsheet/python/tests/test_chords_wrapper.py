"""Behavioural contract for the MusicDSL-backed chord validator (`tonalis.chords`).

Pins the three classes of token the wrapper must get right:
  * real chords (delegated to MusicDSL's ``Chord()``),
  * the non-chord lead-sheet markers MusicDSL rejects but the linter must accept,
  * outright garbage / empty.
The frozen-oracle reconciliation (``test_chord_reconciliation``) proves verdict-identity
with the retired regex over the whole corpus; this file keeps the human-readable contract.
"""

from tonalis.chords import is_valid_chord


def test_real_chords_valid():
    for t in ["C^7", "A-7", "G7", "F#o7", "Bh7", "Csus", "C7b9", "G7#11", "C/E", "C69", "Fadd9"]:
        assert is_valid_chord(t), t


def test_ireal_sus_shorthand_valid():
    # bare-4 sus shorthand: MusicDSL now constructs these (taught in Task 3)
    for t in ["C4", "A4", "G4", "A4/C", "D#4", "Gb4", "E4/G"]:
        assert is_valid_chord(t), t


def test_ireal_seven_plus_valid():
    # X7+ raised-5th form (== X7#5): MusicDSL now constructs these (taught in Task 4).
    # The layout-star variant Bb*7+* strips to Bb7+ and is likewise valid.
    for t in ["C7+", "Bb7+", "Eb7+", "Bb7+/F", "Bb*7+*"]:
        assert is_valid_chord(t), t


def test_non_chord_cases_preserved():
    # the cases MusicDSL's Chord() alone REJECTS but the grammar whitelisted
    for t in ["N.C.", "n", "/A", "Bb*7"]:
        assert is_valid_chord(t), t


def test_rejects_garbage_and_empty():
    for t in ["", "Cmaj7", "xyzzy", "H7"]:
        assert not is_valid_chord(t), t


def test_rejects_more_garbage():
    """Additional negative coverage: tokens that look plausibly chord-shaped but are invalid.

    ``Cmaj7``  — wrong dialect: MusicDSL uses ``^`` for major-7, not ``maj``
    ``H7``     — no note letter H exists in Western notation
    ``Cxyzzy`` — nonsense extension suffix
    ``C#b``    — contradictory double accidental (sharp + flat on the same root)
    """
    for t in ["Cmaj7", "H7", "Cxyzzy", "C#b"]:
        assert is_valid_chord(t) is False, (
            f"Expected is_valid_chord({t!r}) to be False, but it returned True — "
            "stop and report this as a real finding; do not weaken the assertion."
        )


def test_rejects_malformed_old_grammar_wrongly_accepted():
    # the genuinely-malformed token the OLD regex wrongly accepted; MusicDSL (correctly)
    # rejects it. This is the sole blessed divergence in the reconciliation oracle.
    # (C7+ / Bb*7+* were previously here but are real chords MusicDSL was taught in Task 4.)
    for t in ["C7777"]:
        assert not is_valid_chord(t), t
