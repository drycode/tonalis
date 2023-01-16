from hypothesis import given
from hypothesis import strategies as st

from music_dsl.domain.chords.numeric_chord import NumericChord
from music_dsl.domain.static import TWELVE_TONES, Notes, ScaleDegree
from music_dsl.helpers import get_index
from music_dsl.builders import build_from_chord_string
from music_dsl.transactions import _get_key
from tests.testdata.fuzzy_test_supersets import (
    EXAMPLE_MULTI_DIM_CHORDS,
    EXAMPLE_NUMERIC_STRS,
)
from tests.testdata.other_intentional import EXAMPLE_CHORD_STRS


@given(st.sampled_from(Notes))
def test_get_index_notes(note):
    if not isinstance(note.value, dict):
        assert 12 > get_index(note) >= 0


@given(st.sampled_from(ScaleDegree))
def test_get_index_scale_degree(note):
    if not isinstance(note.value, dict):
        assert 12 > get_index(note.normalized()) >= 0


@given(st.sampled_from(EXAMPLE_CHORD_STRS), st.sampled_from(EXAMPLE_NUMERIC_STRS))
def test_get_key(chord_segment, pattern):
    assert (
        _get_key(
            build_from_chord_string(chord_segment),
            build_from_chord_string(pattern, NumericChord),
        )
        in TWELVE_TONES
    )


@given(st.sampled_from(EXAMPLE_MULTI_DIM_CHORDS))
def test_multi_dimensional_numeric_chord(pattern):
    """
    Strings are getting converted into NumericChord types, whose repr should return back
    the original string, but does so recursively by reading attributes on the NumericChord
    class
    """
    numerator, denominator = pattern.split("/")
    expected = (
        numerator + "/" + denominator
        if ("-" not in numerator and "h" not in numerator and "o" not in numerator)
        else numerator.lower() + "/" + denominator
    )
    assert str(build_from_chord_string(pattern, NumericChord)) == expected
