"""Executes conformance/music-dsl cases against the Python music_dsl reference.
The op dispatch IS the cross-port contract: TS/Rust runners implement the same op names."""
import json
import sys
from pathlib import Path

from music_dsl.domain.static import Intervals, Notes, ScaleDegree, Triad, Seventh, Extensions
from music_dsl.encode import Encoding, Scales
from music_dsl.helpers import get_index, strip_left, strip_right, semitones_apart_ascending
from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
from music_dsl.domain.chords.numeric_chord import NumericChord, IncorrectHarmonicFunctionException
from music_dsl.transactions import modulate, is_diatonic, harmonic_function_in_key, chord_in_key
from music_dsl.serialize import serialize_chord, serialize_numeric_chord, serialize_measure
from music_dsl.realize import (
    note_to_midi, midi_to_hz, interval_pitches, chord_pitches, scale_pitches, scale_degree_pitch,
)
from music_dsl.domain.time import TimeSignature
from music_dsl.domain.time.measure import Measure, BeatType

CASES = Path(__file__).resolve().parents[2] / "cases"


def _encoding_value(triad, seventh, extensions):
    enc = Encoding(
        root=Notes.C,
        triad=Triad[triad],
        _7th=Seventh[seventh],
        extensions=[Extensions[e] for e in extensions],
    )
    return enc.value


def _parse_chord(input):
    """parse_chord op: returns {"chord": <model>} or raises InvalidChordStringException."""
    return {"chord": serialize_chord(Chord(input))}


def _encode_chord(input):
    """encode_chord op: returns the integer encoding value for the given chord string."""
    return Chord(input).encoding


def _parse_numeric(input):
    """parse_numeric op: returns {"numeric": <model>} where model has numerator/denominator."""
    nc = NumericChord.from_chord_string(input)
    return {"numeric": serialize_numeric_chord(nc)}


def _numeric_from_chord(key_root, chord, substitution):
    """numeric_from_chord op: build attrs from _from_chord and serialize.

    Maps IncorrectHarmonicFunctionException / InvalidChordStringException -> error sentinel.
    """
    attrs = NumericChord._from_chord(Notes(key_root), Chord(chord), substitution)
    from music_dsl.serialize import _serialize_chord_attrs
    return {"numeric": _serialize_chord_attrs(attrs)}


def _modulate(semitones, note):
    """modulate op: transpose a Notes or ScaleDegree value by semitones.

    ``note`` is treated as a ScaleDegree value if it matches one, else as a Notes value.
    Returns the resulting .value string.
    """
    try:
        n = ScaleDegree(note)
    except ValueError:
        n = Notes(note)
    return modulate(semitones, n).value


def _is_diatonic(root, scale, chord):
    """is_diatonic op: bool — is chord diatonic to the scale rooted at root?

    ``scale`` is a Scales member NAME (e.g. "Major", "Minor", "HarmonicMinor").
    """
    return is_diatonic(Notes(root), Scales[scale], Chord(chord))


def _harmonic_function_in_key(key_root, key_is_minor, chord):
    """harmonic_function_in_key op: returns the HarmonicFunctions NAME."""
    return harmonic_function_in_key(Notes(key_root), key_is_minor, Chord(chord)).name


def _chord_in_key(numeric, key_root):
    """chord_in_key op: realize a numeric chord string to an absolute Chord and serialize."""
    nc = NumericChord.from_chord_string(numeric)
    realized = chord_in_key(nc, Notes(key_root))
    return {"chord": serialize_chord(realized)}


# Build 5: realize + time ops

def _note_to_midi(note, octave=4):
    """note_to_midi op: MIDI number for note at octave."""
    return note_to_midi(Notes(note), octave)


def _midi_to_hz(midi):
    """midi_to_hz op: equal-tempered frequency, rounded to 4 decimal places."""
    return round(midi_to_hz(midi), 4)


def _interval_pitches(root, interval, octave=4):
    """interval_pitches op: [root_midi, upper_midi] for the interval above root."""
    return interval_pitches(Notes(root), Intervals[interval], octave)


def _chord_pitches(chord, octave=4):
    """chord_pitches op: list of MIDI notes for chord in root position."""
    return chord_pitches(Chord(chord), octave)


def _scale_pitches(key_root, scale, octave=4):
    """scale_pitches op: ascending MIDI notes tonic-to-tonic for the named scale."""
    return scale_pitches(Notes(key_root), Scales[scale], octave)


def _scale_degree_pitch(degree, key_root, octave=4):
    """scale_degree_pitch op: MIDI pitch for a ScaleDegree in the given key."""
    return scale_degree_pitch(ScaleDegree(degree), Notes(key_root), octave)


def _parse_measure(m_number, numerator, denominator, raw_measure):
    """parse_measure op: build Measure and serialize to {"measure": <model>}.

    Propagates InvalidChordStringException (or any exception from Chord construction)
    so that conformance error cases can use expect.error.
    """
    m = Measure(m_number, TimeSignature(numerator, denominator), raw_measure, BeatType, Chord)
    return {"measure": serialize_measure(m)}


OPS = {
    "intervals_equal":   lambda a, b: Intervals[a] == Intervals[b],
    "interval_semitones": lambda x: int(Intervals[x]),
    "notes_equal":       lambda a, b: Notes(a) == Notes(b),
    "note_index":        lambda n: get_index(Notes(n)),  # chromatic index 0-11 (TWELVE_TONES position)
    "scale_degrees_equal": lambda a, b: ScaleDegree(a) == ScaleDegree(b),
    "scale_value":               lambda name: Scales[name].value.mask,
    "encoding_value":            _encoding_value,
    "strip_left":                lambda bits, x: strip_left(bits, x),
    "strip_right":               lambda bits, x: strip_right(bits, x),
    "semitones_apart_ascending": lambda root, note: semitones_apart_ascending(Notes(root), Notes(note)),
    "parse_chord":               lambda input: _parse_chord(input),
    "encode_chord":              lambda input: _encode_chord(input),
    # Build 4: numeric + transactions ops
    "parse_numeric":             lambda input: _parse_numeric(input),
    "numeric_from_chord":        lambda key_root, chord, substitution: _numeric_from_chord(key_root, chord, substitution),
    "modulate":                  lambda semitones, note: _modulate(semitones, note),
    "is_diatonic":               lambda root, scale, chord: _is_diatonic(root, scale, chord),
    "harmonic_function_in_key":  lambda key_root, key_is_minor, chord: _harmonic_function_in_key(key_root, key_is_minor, chord),
    "chord_in_key":              lambda numeric, key_root: _chord_in_key(numeric, key_root),
    # Build 5: realize + time ops
    "note_to_midi":              lambda note, octave=4: _note_to_midi(note, octave),
    "midi_to_hz":                lambda midi: _midi_to_hz(midi),
    "interval_pitches":          lambda root, interval, octave=4: _interval_pitches(root, interval, octave),
    "chord_pitches":             lambda chord, octave=4: _chord_pitches(chord, octave),
    "scale_pitches":             lambda key_root, scale, octave=4: _scale_pitches(key_root, scale, octave),
    "scale_degree_pitch":        lambda degree, key_root, octave=4: _scale_degree_pitch(degree, key_root, octave),
    "parse_measure":             lambda m_number, numerator, denominator, raw_measure: _parse_measure(m_number, numerator, denominator, raw_measure),
}


def run():
    failures = []
    total = 0
    for case_file in sorted(CASES.rglob("*.json")):
        for case in json.loads(case_file.read_text()):
            total += 1
            expect = case["expect"]
            if "error" in expect:
                # Error cases: the op must raise; any exception counts as passing.
                try:
                    OPS[case["op"]](**case["args"])
                    failures.append(f"{case['name']}: op={case['op']} args={case['args']} expected error but got a value")
                except Exception:
                    pass  # error expected and raised — pass
                continue
            # Execute the op; map any exception to a failure (non-error cases must not raise).
            try:
                got = OPS[case["op"]](**case["args"])
            except Exception as exc:
                failures.append(f"{case['name']}: op={case['op']} args={case['args']} raised unexpectedly: {exc}")
                continue
            if "model" in expect:
                # Model ops (parse_chord etc.): compare the whole dict.
                want = expect["model"]
                if got != want:
                    failures.append(f"{case['name']}: op={case['op']} args={case['args']} got={got} want={want}")
            else:
                # Function/scalar ops: compare the scalar value.
                want = expect["value"]
                if got != want:
                    failures.append(f"{case['name']}: op={case['op']} args={case['args']} got={got} want={want}")
    if failures:
        print(f"{len(failures)}/{total} FAILED:")
        print("\n".join("  " + f for f in failures))
        return 1
    print(f"music-dsl conformance: {total}/{total} passed")
    return 0


if __name__ == "__main__":
    sys.exit(run())
