"""Sanity tests for music_dsl.serialize.serialize_numeric_chord.

These are ADDITIVE — they verify the new serializer without modifying any
existing domain class or test.
"""
import json

import pytest

from music_dsl.domain.chords.numeric_chord import NumericChord
from music_dsl.domain.chords.abstract_chord import ChordAttrs
from music_dsl.serialize import serialize_numeric_chord


class TestSerializeNumericChordShape:
    """serialize_numeric_chord emits {numerator, denominator} with the canonical chord-model."""

    def test_v7_slash_v_has_numerator_and_denominator(self):
        nc = NumericChord.from_chord_string("V7/V")
        result = serialize_numeric_chord(nc)
        assert set(result.keys()) == {"numerator", "denominator"}

    def test_v7_slash_v_numerator_root_is_V(self):
        nc = NumericChord.from_chord_string("V7/V")
        result = serialize_numeric_chord(nc)
        assert result["numerator"]["root"] == "V"

    def test_v7_slash_v_denominator_root_is_V(self):
        nc = NumericChord.from_chord_string("V7/V")
        result = serialize_numeric_chord(nc)
        assert result["denominator"] is not None
        assert result["denominator"]["root"] == "V"

    def test_v7_no_slash_denominator_is_null(self):
        nc = NumericChord.from_chord_string("V7")
        result = serialize_numeric_chord(nc)
        assert result["denominator"] is None

    def test_numerator_has_all_required_keys(self):
        nc = NumericChord.from_chord_string("ii-7")
        result = serialize_numeric_chord(nc)
        expected_keys = {"root", "triad", "seventh", "extensions", "harmonic_function", "substitution"}
        assert set(result["numerator"].keys()) == expected_keys

    def test_ii_minor7_numerator_fields(self):
        nc = NumericChord.from_chord_string("ii-7")
        result = serialize_numeric_chord(nc)
        num = result["numerator"]
        assert num["root"] == "ii"
        assert num["triad"] == "-"
        assert num["seventh"] == "7"
        assert num["extensions"] == []
        assert num["harmonic_function"] == "Subdominant"
        assert num["substitution"] is False

    def test_json_roundtrip(self):
        nc = NumericChord.from_chord_string("V7/V")
        result = serialize_numeric_chord(nc)
        serialised = json.dumps(result)
        restored = json.loads(serialised)
        assert restored == result

    def test_no_bass_or_encoding_in_numerator(self):
        nc = NumericChord.from_chord_string("V7")
        result = serialize_numeric_chord(nc)
        assert "bass" not in result["numerator"]
        assert "encoding" not in result["numerator"]

    def test_substitution_prefix_sV7(self):
        nc = NumericChord.from_chord_string("sV7")
        result = serialize_numeric_chord(nc)
        assert result["numerator"]["substitution"] is True

    def test_bVI_major7(self):
        nc = NumericChord.from_chord_string("bVI^7")
        result = serialize_numeric_chord(nc)
        assert result["numerator"]["root"] == "bVI"
        assert result["numerator"]["seventh"] == "^7"
        assert result["numerator"]["harmonic_function"] == "Tonic"
