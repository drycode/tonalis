"""Sanity tests for music_dsl.serialize.serialize_chord.

These are ADDITIVE — they verify the new serializer without modifying any
existing domain class or test.
"""
import json

import pytest

from music_dsl.domain.chords.chord import Chord
from music_dsl.serialize import serialize_chord


class TestSerializeChordShape:
    """serialize_chord returns a fully-JSON-serialisable dict with the exact 6 fields."""

    def test_c_major7_sharp11_has_all_keys(self):
        chord = Chord("C^7#11")
        result = serialize_chord(chord)
        assert set(result.keys()) == {"root", "triad", "seventh", "extensions", "harmonic_function", "substitution"}

    def test_c_major7_sharp11_json_roundtrip(self):
        chord = Chord("C^7#11")
        result = serialize_chord(chord)
        # Must be JSON-serialisable (no raw enum objects)
        serialised = json.dumps(result)
        restored = json.loads(serialised)
        assert restored == result

    def test_c_major7_sharp11_documented_shape(self):
        """Cross-check: C^7#11 -> documented field values."""
        chord = Chord("C^7#11")
        result = serialize_chord(chord)
        assert result["root"] == "C"
        assert result["triad"] == ""          # Major triad value
        assert result["seventh"] == "^7"      # Major seventh value
        assert result["extensions"] == ["#11"]
        assert result["harmonic_function"] == "Tonic"
        assert result["substitution"] is False

    def test_c_sharp_minor7_flat_normalized_root(self):
        """C#-7 -> root must be 'Db' (flat-normalised)."""
        chord = Chord("C#-7")
        result = serialize_chord(chord)
        assert result["root"] == "Db"
        assert result["triad"] == "-"
        assert result["seventh"] == "7"
        assert result["harmonic_function"] == "Subdominant"

    def test_g7_is_dominant(self):
        chord = Chord("G7")
        result = serialize_chord(chord)
        assert result["root"] == "G"
        assert result["triad"] == ""
        assert result["seventh"] == "7"
        assert result["harmonic_function"] == "Dominant"
        assert result["substitution"] is False

    def test_c_minor_triad_value(self):
        chord = Chord("C-")
        result = serialize_chord(chord)
        assert result["triad"] == "-"
        assert result["seventh"] == ""

    def test_extensions_list_order_preserved(self):
        """Extensions must be in parse order and serialised by .value."""
        chord = Chord("C7b9#11")
        result = serialize_chord(chord)
        assert result["extensions"] == ["b9", "#11"]

    def test_no_bass_or_encoding_field(self):
        chord = Chord("C^7/E")
        result = serialize_chord(chord)
        assert "bass" not in result
        assert "encoding" not in result
        # Bass was discarded; root is still C
        assert result["root"] == "C"

    def test_harmonic_function_by_name_not_value(self):
        """harmonic_function must be the NAME (Tonic/Dominant/Subdominant), not auto() int."""
        for chord_str, expected_hf in [("C^7", "Tonic"), ("G7", "Dominant"), ("D-7", "Subdominant")]:
            chord = Chord(chord_str)
            result = serialize_chord(chord)
            assert result["harmonic_function"] == expected_hf, f"{chord_str}: {result['harmonic_function']!r} != {expected_hf!r}"

    def test_substitution_is_bool_false_for_absolute_chords(self):
        """Absolute Chord instances never set substitution=True."""
        chord = Chord("C7")
        result = serialize_chord(chord)
        assert isinstance(result["substitution"], bool)
        assert result["substitution"] is False
