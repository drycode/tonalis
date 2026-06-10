"""Pitch realization — turn theory objects into concrete pitches.

The bridge from the symbolic domain (Notes, Intervals, Chords, scale degrees) to
**sound**: MIDI note numbers and frequencies. This is the foundation the
ear-trainer is built on (and is reusable anywhere theory needs to become audio).

Conventions: MIDI middle C = C4 = 60; A4 = 69 = 440 Hz. All functions are pure
and deterministic — easy to assert on exact integers.
"""

from __future__ import annotations

from typing import List, Union

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.static import Intervals, Notes, ScaleDegree, Seventh, Triad
from music_dsl.encode import EncodingMap, Scales
from music_dsl.helpers import get_index, semitones_apart_ascending
from music_dsl.transactions import modulate

DEFAULT_OCTAVE = 4
A4_MIDI = 69
A4_HZ = 440.0


def _pitch_class(note: Notes) -> int:
    """Semitones above C (0-11), enharmonic-safe."""
    return semitones_apart_ascending(Notes.C, note)


def note_to_midi(note: Notes, octave: int = DEFAULT_OCTAVE) -> int:
    """MIDI number for a note in an octave. note_to_midi(C, 4) == 60."""
    return 12 * (octave + 1) + _pitch_class(note)


def midi_to_hz(midi: int) -> float:
    """Equal-tempered frequency for a MIDI number. midi_to_hz(69) == 440.0."""
    return A4_HZ * 2 ** ((midi - A4_MIDI) / 12)


def note_to_hz(note: Notes, octave: int = DEFAULT_OCTAVE) -> float:
    return midi_to_hz(note_to_midi(note, octave))


def _semitones(interval: Union[Intervals, int]) -> int:
    return getattr(interval, "value", interval)


def interval_pitches(
    root: Notes, interval: Union[Intervals, int], octave: int = DEFAULT_OCTAVE
) -> List[int]:
    """The two MIDI notes of an interval above a root."""
    base = note_to_midi(root, octave)
    return [base, base + _semitones(interval)]


def chord_pitches(chord: Chord, octave: int = DEFAULT_OCTAVE) -> List[int]:
    """MIDI notes of a chord (root position), read straight from EncodingMap's
    semitone offsets — not the lossy 19-bit packed encoding."""
    base = note_to_midi(chord.root, octave)
    seventh = list(EncodingMap[chord._7th])
    # A diminished triad with a seventh is a diminished-7th chord: its seventh is
    # a *diminished* 7th (9 semitones), not the minor 7th (10) the shared
    # Seventh.Minor entry encodes. (HalfDiminished keeps the minor 7th.)
    if chord.triad == Triad.Diminished and chord._7th == Seventh.Minor:
        seventh = [9]
    offsets = [0] + list(EncodingMap[chord.triad]) + seventh
    for ext in (chord.extensions or ()):
        offsets += list(EncodingMap.get(ext, []))
    return [base + off for off in sorted(set(offsets))]


def scale_pitches(
    key_root: Notes, scale: Scales = Scales.Major, octave: int = DEFAULT_OCTAVE
) -> List[int]:
    """Ascending MIDI notes of a scale, tonic to tonic (inclusive octave)."""
    base = note_to_midi(key_root, octave)
    size = scale.value.bit_length() // 3          # scale masks are a 12-bit pattern ×3
    top = scale.value >> (2 * size)               # the leading pattern
    pitches = [base + i for i in range(size) if (top >> (size - 1 - i)) & 1]
    pitches.append(base + size)                   # close on the octave
    return pitches


def scale_degree_pitch(
    degree: ScaleDegree, key_root: Notes, octave: int = DEFAULT_OCTAVE
) -> int:
    """MIDI note of a scale degree within a key. (I in C) -> 60, (V in C) -> 67."""
    note = modulate(get_index(degree), key_root)
    return note_to_midi(note, octave)
