"""Property-based robustness + round-trip tests for chord parsing.

These guard the DSL's two load-bearing invariants:

  1. **Robustness contract** -- parsing ANY string raises at most one catchable
     ``InvalidChordStringException``; a malformed input never leaks a raw
     ``ValueError`` / ``IndexError`` / ``KeyError`` / ``TypeError`` from enum
     construction or extension tokenising.
  2. **Round-trip fixed-point** -- a chord's canonical serialization re-parses to
     identical attributes, and a tritone substitution survives the NumericChord
     repr (``subV7/x`` does not collapse to ``V7/x``).

Regression cases at the bottom pin the exact inputs that used to crash.
"""

from hypothesis import given, settings, strategies as st

from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.numeric_chord import NumericChord

# Characters that appear in real chord / numeral notation -- biases the fuzzer
# toward chord-shaped garbage that actually exercises the grammar.
CHORD_ALPHABET = "ABCDEFG#b-^7o6h+sus912354/altmajdiminSV iIvV"

ROOTS = ["C", "C#", "Db", "D", "Eb", "E", "F", "F#", "Gb", "G", "Ab",
         "A", "Bb", "B", "Cb", "Fb", "B#", "E#"]
TRIADS = ["", "-", "o", "h", "+", "sus", "sus2", "sus4"]
SEVENTHS = ["", "7", "^7", "^", "6"]
EXTENSIONS = ["", "b9", "9", "#9", "11", "#11", "b13", "13", "b5", "#5", "alt"]

DEGREES = ["I", "bII", "II", "bIII", "III", "IV", "#IV", "V", "bVI", "VI",
           "bVII", "VII", "i", "ii", "biii", "iii", "iv", "#iv", "v", "vi",
           "bvii", "vii"]
NUM_QUALITIES = ["", "7", "^7", "maj7", "-7", "-", "-7b5", "h7", "o7", "6"]


# --------------------------------------------------------------------------- #
# 1. Robustness contract: garbage in -> clean exception, never a raw crash.
# --------------------------------------------------------------------------- #

@settings(max_examples=600)
@given(st.text(alphabet=CHORD_ALPHABET, max_size=14))
def test_chord_arbitrary_input_only_raises_invalid(s):
    try:
        Chord(s)
    except InvalidChordStringException:
        pass  # the one allowed failure mode


@settings(max_examples=400)
@given(st.text(max_size=10))
def test_chord_unicode_input_only_raises_invalid(s):
    try:
        Chord(s)
    except InvalidChordStringException:
        pass


@settings(max_examples=600)
@given(st.text(alphabet=CHORD_ALPHABET, max_size=14))
def test_numeric_chord_arbitrary_input_only_raises_invalid(s):
    try:
        NumericChord.from_chord_string(s)
    except InvalidChordStringException:
        pass


# --------------------------------------------------------------------------- #
# 2. Round-trip fixed-point for well-formed chords.
# --------------------------------------------------------------------------- #

@given(
    st.sampled_from(ROOTS),
    st.sampled_from(TRIADS),
    st.sampled_from(SEVENTHS),
    st.sampled_from(EXTENSIONS),
)
def test_chord_canonical_form_is_a_parse_fixed_point(root, triad, sev, ext):
    # Scope to the *real* chord grammar: a sharp tension (#9/#11/#5) always rides
    # on a quality token in lead-sheet notation (`C7#9`), never bare after a
    # natural root -- `C#9` legitimately means the C# triad add-9, so a bare
    # root + #-tension is not a distinct chord to round-trip.
    if ext.startswith("#") and not (triad or sev):
        return
    raw = root + triad + sev + ext
    try:
        chord = Chord(raw)
    except InvalidChordStringException:
        return  # not every combination is a legal chord; only round-trip legal ones
    canonical = repr(chord._chord_attrs)
    assert repr(Chord(canonical)._chord_attrs) == canonical


def test_altered_tension_without_seventh_on_natural_root_is_rejected():
    # `B#b9` normalizes its root to C, but a bare-triad b9 with no 7th has no
    # spellable canonical form: repr would emit `Cb9`, which re-parses as Cb+9 -> B
    # add9. Reject it as invalid rather than emit a non-round-tripping repr.
    for bad in ("B#b9", "E#b13", "B#b5"):
        with pytest.raises(InvalidChordStringException):
            Chord(bad)


def test_altered_tension_with_seventh_round_trips():
    # A real altered dominant (7th present) is well-formed and a parse fixed point.
    for good in ("C7b9", "G7#9", "F7b13", "Db7b9"):
        chord = Chord(good)
        canonical = repr(chord._chord_attrs)
        assert repr(Chord(canonical)._chord_attrs) == canonical


def test_non_major_triad_with_flat_tension_round_trips():
    # A quality token ("-"/"o") separates the root from the tension, so there is no
    # root-binding ambiguity even without a 7th -- these stay valid + round-trip.
    for good in ("C-b9", "Cob9"):
        chord = Chord(good)
        canonical = repr(chord._chord_attrs)
        assert repr(Chord(canonical)._chord_attrs) == canonical


@given(
    st.sampled_from(DEGREES),
    st.sampled_from(NUM_QUALITIES),
    st.booleans(),
    st.one_of(st.none(), st.sampled_from(DEGREES)),
)
def test_numeric_chord_round_trips(degree, quality, substitution, denom):
    raw = ("s" if substitution else "") + degree + quality
    if denom is not None:
        raw += "/" + denom
    try:
        nc = NumericChord.from_chord_string(raw)
    except InvalidChordStringException:
        return
    # repr -> re-parse -> repr is idempotent (the canonical form is stable).
    assert repr(NumericChord.from_chord_string(repr(nc))) == repr(nc)


# --------------------------------------------------------------------------- #
# 3. Tritone substitution survives the repr (the bug that started this).
# --------------------------------------------------------------------------- #

def test_substitution_prefix_survives_repr():
    for s in ["sV7/V", "sV7", "sii-7/V", "sV7b9", "sV7/iii"]:
        assert repr(NumericChord.from_chord_string(s)) == s


def test_substitution_is_distinct_from_plain_dominant():
    assert repr(NumericChord.from_chord_string("sV7/V")) != repr(
        NumericChord.from_chord_string("V7/V")
    )


# --------------------------------------------------------------------------- #
# 4. Explicit regression cases -- these exact inputs used to leak raw errors.
# --------------------------------------------------------------------------- #

import pytest


@pytest.mark.parametrize(
    "bad", ["Cadd9add11", "C##", "Cbb", "H", "Z7", "", "Csusalt", "Gsus4alt"]
)
def test_chord_bad_input_regressions(bad):
    with pytest.raises(InvalidChordStringException):
        Chord(bad)


@pytest.mark.parametrize("bad", ["", "/V", "VIII", "K7", "bbII"])
def test_numeric_chord_bad_input_regressions(bad):
    with pytest.raises(InvalidChordStringException):
        NumericChord.from_chord_string(bad)
