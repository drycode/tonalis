"""Executes conformance/music-dsl cases against the Python music_dsl reference.
The op dispatch IS the cross-port contract: TS/Rust runners implement the same op names."""
import json
import sys
from pathlib import Path

from music_dsl.domain.static import Intervals, Notes, ScaleDegree, Triad, Seventh, Extensions
from music_dsl.encode import Encoding, Scales, scan_scale
from music_dsl.helpers import get_index, strip_left, strip_right, semitones_apart_ascending

CASES = Path(__file__).resolve().parents[2] / "cases"


def _encoding_value(triad, seventh, extensions):
    enc = Encoding(
        root=Notes.C,
        triad=Triad[triad],
        _7th=Seventh[seventh],
        extensions=[Extensions[e] for e in extensions],
    )
    return enc.value


OPS = {
    "intervals_equal":   lambda a, b: Intervals[a] == Intervals[b],
    "interval_semitones": lambda x: int(Intervals[x]),
    "notes_equal":       lambda a, b: Notes(a) == Notes(b),
    "note_index":        lambda n: get_index(Notes(n)),  # chromatic index 0-11 (TWELVE_TONES position)
    "scale_degrees_equal": lambda a, b: ScaleDegree(a) == ScaleDegree(b),
    "scale_value":               lambda name: Scales[name].value,
    "encoding_value":            _encoding_value,
    "strip_left":                lambda bits, x: strip_left(bits, x),
    "strip_right":               lambda bits, x: strip_right(bits, x),
    "semitones_apart_ascending": lambda root, note: semitones_apart_ascending(Notes(root), Notes(note)),
    "scan_scale":                lambda scale, chord: scan_scale(scale, chord),
}


def run():
    failures = []
    total = 0
    for case_file in sorted(CASES.rglob("*.json")):
        for case in json.loads(case_file.read_text()):
            total += 1
            expect = case["expect"]
            if "error" in expect:
                try:
                    OPS[case["op"]](**case["args"])
                    failures.append(f"{case['name']}: op={case['op']} args={case['args']} expected error but got a value")
                except Exception:
                    pass  # error expected and raised — pass
                continue
            got = OPS[case["op"]](**case["args"])
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
