"""Bless script: generates conformance cases for realize/ and time/ by running
the Python reference and writing the results to the case files.

Run from the repo root:
    .venv/bin/python conformance/music-dsl/runners/python/bless_realize.py
"""
import json
import sys
from pathlib import Path

# Ensure the music_dsl package is importable (works when run from repo root
# after `pip install -e music-dsl/python`).
from music_dsl.domain.static import Intervals, Notes, ScaleDegree
from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
from music_dsl.encode import Scales
from music_dsl.realize import (
    note_to_midi, midi_to_hz, interval_pitches, chord_pitches,
    scale_pitches, scale_degree_pitch,
)
from music_dsl.domain.time import TimeSignature
from music_dsl.domain.time.measure import Measure, BeatType
from music_dsl.serialize import serialize_measure

CASES_ROOT = Path(__file__).resolve().parents[2] / "cases"
REALIZE_DIR = CASES_ROOT / "realize"
TIME_DIR = CASES_ROOT / "time"

REALIZE_DIR.mkdir(parents=True, exist_ok=True)
TIME_DIR.mkdir(parents=True, exist_ok=True)


def _write(path: Path, cases: list) -> None:
    path.write_text(json.dumps(cases, indent=2) + "\n")
    print(f"  wrote {len(cases)} cases → {path}")


# ---------------------------------------------------------------------------
# realize/midi.json  — note_to_midi
# ---------------------------------------------------------------------------

def bless_midi():
    cases = []

    def add(name, note, octave, expected):
        cases.append({
            "name": f"realize/midi/{name}",
            "op": "note_to_midi",
            "args": {"note": note, "octave": octave},
            "expect": {"value": expected},
        })

    add("middle-C", "C", 4, note_to_midi(Notes("C"), 4))
    add("A440", "A", 4, note_to_midi(Notes("A"), 4))
    add("C5", "C", 5, note_to_midi(Notes("C"), 5))
    add("C3", "C", 3, note_to_midi(Notes("C"), 3))
    add("G4", "G", 4, note_to_midi(Notes("G"), 4))
    add("Db4-flat-normalised", "Db", 4, note_to_midi(Notes("Db"), 4))
    add("B4", "B", 4, note_to_midi(Notes("B"), 4))
    add("Bb4", "Bb", 4, note_to_midi(Notes("Bb"), 4))
    add("C-octave-1", "C", 1, note_to_midi(Notes("C"), 1))

    _write(REALIZE_DIR / "midi.json", cases)


# ---------------------------------------------------------------------------
# realize/hz.json  — midi_to_hz
# ---------------------------------------------------------------------------

def bless_hz():
    cases = []

    def add(name, midi):
        cases.append({
            "name": f"realize/hz/{name}",
            "op": "midi_to_hz",
            "args": {"midi": midi},
            "expect": {"value": round(midi_to_hz(midi), 4)},
        })

    add("A440-midi69", 69)
    add("middle-C-midi60", 60)
    add("C5-midi72", 72)
    add("A5-midi81", 81)
    add("A3-midi57", 57)

    _write(REALIZE_DIR / "hz.json", cases)


# ---------------------------------------------------------------------------
# realize/intervals.json  — interval_pitches
# ---------------------------------------------------------------------------

def bless_intervals():
    cases = []

    def add(name, root, interval, octave):
        result = interval_pitches(Notes(root), Intervals[interval], octave)
        cases.append({
            "name": f"realize/intervals/{name}",
            "op": "interval_pitches",
            "args": {"root": root, "interval": interval, "octave": octave},
            "expect": {"value": result},
        })

    add("C4-P5", "C", "P5", 4)
    add("C4-M3", "C", "M3", 4)
    add("C4-m3", "C", "m3", 4)
    add("C4-Tritone", "C", "Tritone", 4)
    add("C4-Octave", "C", "Octave", 4)
    add("G4-P5", "G", "P5", 4)
    add("A4-M3", "A", "M3", 4)
    add("C4-m7", "C", "m7", 4)
    add("C4-M7", "C", "M7", 4)

    _write(REALIZE_DIR / "intervals.json", cases)


# ---------------------------------------------------------------------------
# realize/chords.json  — chord_pitches
# ---------------------------------------------------------------------------

def bless_chords():
    cases = []

    def add(name, chord_str, octave=4):
        result = chord_pitches(Chord(chord_str), octave)
        cases.append({
            "name": f"realize/chords/{name}",
            "op": "chord_pitches",
            "args": {"chord": chord_str, "octave": octave},
            "expect": {"value": result},
        })

    add("C-maj7", "C^7")
    add("C-min7", "C-7")
    add("C-dom7", "C7")
    add("C-dim7", "Co7")          # diminished 7th = 9 semitones
    add("C-half-dim", "Ch7")      # half-dim = minor 7th = 10 semitones
    add("C7b9-extension", "C7b9") # b9 encoded as octave (12 semitones)
    add("C13-no-b7", "C13")       # 13th without adding b7
    add("G7-dominant", "G7")
    add("F-maj7", "F^7")
    add("Co7add9", "Co7add9")     # dim7 + 9th
    add("C-aug", "C+")
    add("C-sus4", "Csus4")
    add("C5-octave-override", "C^7", 5)

    _write(REALIZE_DIR / "chords.json", cases)


# ---------------------------------------------------------------------------
# realize/scales.json  — scale_pitches
# ---------------------------------------------------------------------------

def bless_scales():
    cases = []

    def add(name, root, scale, octave=4):
        result = scale_pitches(Notes(root), Scales[scale], octave)
        cases.append({
            "name": f"realize/scales/{name}",
            "op": "scale_pitches",
            "args": {"key_root": root, "scale": scale, "octave": octave},
            "expect": {"value": result},
        })

    add("C-major", "C", "Major")
    add("C-minor", "C", "Minor")
    add("C-harmonic-minor", "C", "HarmonicMinor")
    add("G-major", "G", "Major")
    add("F-major", "F", "Major")
    add("Bb-major", "Bb", "Major")

    _write(REALIZE_DIR / "scales.json", cases)


# ---------------------------------------------------------------------------
# realize/degrees.json  — scale_degree_pitch
# ---------------------------------------------------------------------------

def bless_degrees():
    cases = []

    def add(name, degree, root, octave=4):
        result = scale_degree_pitch(ScaleDegree(degree), Notes(root), octave)
        cases.append({
            "name": f"realize/degrees/{name}",
            "op": "scale_degree_pitch",
            "args": {"degree": degree, "key_root": root, "octave": octave},
            "expect": {"value": result},
        })

    add("I-in-C", "I", "C")       # 60
    add("ii-in-C", "ii", "C")     # 62
    add("iii-in-C", "iii", "C")   # 64
    add("IV-in-C", "IV", "C")     # 65
    add("V-in-C", "V", "C")       # 67
    add("vi-in-C", "vi", "C")     # 69
    add("VII-in-C", "VII", "C")   # 71
    add("I-in-G", "I", "G")       # 67
    add("bII-in-C", "bII", "C")   # 61 (Neapolitan)
    add("bVI-in-C", "bVI", "C")   # 68

    _write(REALIZE_DIR / "degrees.json", cases)


# ---------------------------------------------------------------------------
# time/timesig.json  — TimeSignature data only (verified via parse_measure)
# A lightweight set that confirms the time_signature field in the measure output.
# We reuse parse_measure to observe the time_sig field without a separate op.
# ---------------------------------------------------------------------------

def _parse_measure_result(m_number, numerator, denominator, raw_measure):
    """Returns the model dict or None on InvalidChordStringException."""
    try:
        m = Measure(m_number, TimeSignature(numerator, denominator), raw_measure, BeatType, Chord)
        return {"measure": serialize_measure(m)}
    except InvalidChordStringException:
        return None  # caller will emit an error case


def bless_timesig():
    cases = []

    def add(name, m_number, numerator, denominator, raw_measure):
        result = _parse_measure_result(m_number, numerator, denominator, raw_measure)
        # Only assert on the time_signature sub-field via a model case.
        # We capture the full model so it cross-ports correctly.
        cases.append({
            "name": f"time/timesig/{name}",
            "op": "parse_measure",
            "args": {
                "m_number": m_number,
                "numerator": numerator,
                "denominator": denominator,
                "raw_measure": raw_measure,
            },
            "expect": {"model": result},
        })

    add("4-4-single-chord", 1, 4, 4, "C^7")
    add("3-4-single-chord", 8, 3, 4, "G7")
    add("6-8-two-chords", 6, 6, 8, "C^7 D-7")

    _write(TIME_DIR / "timesig.json", cases)


# ---------------------------------------------------------------------------
# time/measure.json  — parse_measure (full Measure serialization)
# ---------------------------------------------------------------------------

def bless_measures():
    cases = []

    def add(name, m_number, numerator, denominator, raw_measure):
        result = _parse_measure_result(m_number, numerator, denominator, raw_measure)
        if result is None:
            # InvalidChordStringException was raised — this is an error case
            cases.append({
                "name": f"time/measure/{name}",
                "op": "parse_measure",
                "args": {
                    "m_number": m_number,
                    "numerator": numerator,
                    "denominator": denominator,
                    "raw_measure": raw_measure,
                },
                "expect": {"error": True},
            })
        else:
            cases.append({
                "name": f"time/measure/{name}",
                "op": "parse_measure",
                "args": {
                    "m_number": m_number,
                    "numerator": numerator,
                    "denominator": denominator,
                    "raw_measure": raw_measure,
                },
                "expect": {"model": result},
            })

    # Core doubling — 2 chords in 4/4, interior doubled: [C^7, C^7, D-7, D-7]
    add("two-chords-doubled-4-4", 1, 4, 4, "C^7 D-7")
    # Empty — all null slots
    add("empty-4-4", 2, 4, 4, "")
    # Single chord — fills all 4 beats: [C^7 * 4]
    add("single-chord-pad-4-4", 3, 4, 4, "C^7")
    # Trailing delimiter — same as single chord (trailing empty stripped)
    add("trailing-delimiter-4-4", 4, 4, 4, "C^7 ")
    # Literal % in chord string — raises InvalidChordStringException → error case
    add("literal-percent-error-4-4", 5, 4, 4, "F^7 % Eh A7")
    # Over-full measure — 5 beats > 4 denominator; no truncation
    add("overfull-five-beats-4-4", 7, 4, 4, "F^7 Eh A7")
    # Over-full measure — 5 tokens, 9 slots (trailing token NOT doubled); most extreme %-doubling
    add("overfull-nine-beats-4-4", 9, 4, 4, "C^7 A-7 D-7 G7 C^7")
    # 6/8 — denominator=8, two chords → total_beats=3, size=max(8,3)=8
    add("two-chords-6-8", 6, 6, 8, "C^7 D-7")
    # 3/4 — denominator=4, single chord, size=max(4,1)=4 beats
    add("single-chord-3-4", 8, 3, 4, "G7")
    # measure number 0 (edge case)
    add("measure-zero", 0, 4, 4, "C^7 D-7")

    _write(TIME_DIR / "measure.json", cases)


if __name__ == "__main__":
    print("Blessing realize + time conformance cases …")
    bless_midi()
    bless_hz()
    bless_intervals()
    bless_chords()
    bless_scales()
    bless_degrees()
    bless_timesig()
    bless_measures()
    print("Done.")
