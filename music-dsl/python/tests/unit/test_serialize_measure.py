"""Sanity tests for music_dsl.serialize.serialize_measure.

These are ADDITIVE — they verify the new serializer without modifying any
existing domain class or test.
"""
import json

import pytest

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.time import TimeSignature
from music_dsl.domain.time.measure import BeatType, Measure
from music_dsl.serialize import serialize_measure


def _make_measure(m_number: int, numerator: int, denominator: int, raw: str) -> Measure:
    return Measure(m_number, TimeSignature(numerator, denominator), raw, BeatType, Chord)


class TestSerializeMeasureShape:
    """serialize_measure returns the canonical dict shape."""

    def test_has_required_top_level_keys(self):
        m = _make_measure(1, 4, 4, "C^7")
        result = serialize_measure(m)
        assert set(result.keys()) == {"m_number", "time_signature", "beat_containers"}

    def test_time_signature_shape(self):
        m = _make_measure(1, 4, 4, "C^7")
        ts = serialize_measure(m)["time_signature"]
        assert ts == {"numerator": 4, "denominator": 4}

    def test_m_number_preserved(self):
        m = _make_measure(7, 4, 4, "G7")
        assert serialize_measure(m)["m_number"] == 7

    def test_json_roundtrip(self):
        m = _make_measure(1, 4, 4, "C^7 D-7")
        result = serialize_measure(m)
        restored = json.loads(json.dumps(result))
        assert restored == result


class TestSerializeMeasureTwoChords:
    """'C^7 D-7' in 4/4 — interior doubling: [C^7, C^7, D-7, D-7]."""

    def setup_method(self):
        self.m = _make_measure(1, 4, 4, "C^7 D-7")
        self.result = serialize_measure(self.m)

    def test_four_beat_containers(self):
        assert len(self.result["beat_containers"]) == 4

    def test_no_null_slots(self):
        assert all(bc is not None for bc in self.result["beat_containers"])

    def test_chord_names(self):
        chords = [bc["chord"]["root"] + bc["chord"]["seventh"] for bc in self.result["beat_containers"]]
        assert chords == ["C^7", "C^7", "D7", "D7"]  # D-7 has root=D, seventh=7

    def test_beat_locations_ascending(self):
        for i, bc in enumerate(self.result["beat_containers"]):
            assert bc["beat_location"]["beat_number"] == i
            assert bc["beat_location"]["measure_number"] == 1


class TestSerializeMeasureEmpty:
    """Empty raw_measure → all null slots."""

    def test_empty_4_4_has_four_null_slots(self):
        m = _make_measure(2, 4, 4, "")
        result = serialize_measure(m)
        assert result["beat_containers"] == [None, None, None, None]

    def test_empty_3_4_has_four_null_slots(self):
        # 3/4 has denominator 4, so size = max(4, 0) = 4
        m = _make_measure(2, 3, 4, "")
        result = serialize_measure(m)
        # total_beats=0, size=max(4,0)=4
        assert result["beat_containers"] == [None, None, None, None]


class TestSerializeMeasureSingleChord:
    """Single chord in 4/4 → padded to fill all 4 beats."""

    def test_single_chord_fills_four_beats(self):
        m = _make_measure(3, 4, 4, "C^7")
        result = serialize_measure(m)
        assert len(result["beat_containers"]) == 4
        assert all(bc is not None for bc in result["beat_containers"])
        assert all(bc["chord"]["root"] == "C" for bc in result["beat_containers"])

    def test_trailing_delimiter_same_as_single(self):
        m1 = _make_measure(1, 4, 4, "C^7")
        m2 = _make_measure(1, 4, 4, "C^7 ")
        r1 = serialize_measure(m1)
        r2 = serialize_measure(m2)
        assert r1["beat_containers"] == r2["beat_containers"]


class TestSerializeMeasureOverfull:
    """Over-full measure — more chord-beats than denominator — no truncation."""

    def test_overfull_5_beats_in_4_4(self):
        # "F^7 Eh A7" = F^7(×2) + Eh(×2) + A7(×1) = 5 slots; size=max(4,5)=5
        m = _make_measure(7, 4, 4, "F^7 Eh A7")
        result = serialize_measure(m)
        assert len(result["beat_containers"]) == 5


class TestSerializeMeasure6_8:
    """6/8 — denominator=8, 2 chords → size=max(8,3)=8 slots."""

    def test_two_chords_in_6_8_gives_8_slots(self):
        m = _make_measure(6, 6, 8, "C^7 D-7")
        result = serialize_measure(m)
        assert len(result["beat_containers"]) == 8
        assert result["time_signature"] == {"numerator": 6, "denominator": 8}
