import pytest
from attr import s
from hypothesis import given
from hypothesis import strategies as st

from music_dsl.domain.chords.numeric_chord import NumericChord
from music_dsl.domain.static import SCALE_DEGREES, Notes, ScaleDegree
from music_dsl.transactions import modulate


@pytest.mark.parametrize(
    ["semitones", "_input", "_expected"],
    ((1, Notes.C, Notes.Db), (6, Notes.C, Notes.Fs)),
)
def test_modulate(semitones: int, _input: Notes, _expected: Notes):
    assert modulate(semitones, _input) == _expected


@given(st.sampled_from(Notes), st.integers(-25, 25))
def test_fuzz_modulate_notes(root, semitones):
    if not isinstance(root.value, dict):
        result = modulate(semitones, root)
        assert root == modulate(-semitones, result)


@given(st.sampled_from(ScaleDegree), st.integers(-25, 25))
def test_fuzz_modulate_scale_degree(root, semitones):
    if not isinstance(root.value, dict):
        result = modulate(semitones, root)
        assert root == modulate(-semitones, result)


@given(root=st.sampled_from(Notes), note=st.sampled_from(Notes))
def test_fuzz_find_scale_degree(root, note):
    if not isinstance(root.value, dict) and not isinstance(note.value, dict):
        scale_degree = NumericChord._find_scale_degree(root, note)
        assert scale_degree in SCALE_DEGREES
