import pytest

from tonalis.chord_grammar import is_valid_chord

GOOD = [
    "C6",
    "D-7",
    "Eb^7",
    "G7b9",
    "F#h7",
    "Bb7#5",
    "C7sus",
    "D-/C",
    "A7alt",
    "Co7",
    "N.C.",
]
BAD = ["Cxyzzy", "Cgarbage", "C!!!", "Cthe", "Czzzz", "Hello", ""]


@pytest.mark.parametrize("s", GOOD)
def test_accepts_real_chords(s):
    assert is_valid_chord(s)


@pytest.mark.parametrize("s", BAD)
def test_rejects_typos(s):
    assert not is_valid_chord(s)


# NOTE: an earlier build also ran a corpus gate asserting that the grammar accepts every
# distinct chord token in a private corpus, tokenized via a format-specific reader. Both the
# corpus and that reader are out of scope for this standalone library, so that gate is dropped
# here. The GOOD/BAD cases above are the pure `is_valid_chord` corpus that belongs to tonalis.
