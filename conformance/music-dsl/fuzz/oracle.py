"""Run each fuzz input through the Python reference and record results as the oracle.

Reads:  conformance/music-dsl/fuzz/inputs.json
Writes: conformance/music-dsl/fuzz/python_out.json

Each output record is one of:
    {"name": ..., "kind": "chord",              "input": ..., "result": <model_dict>}
    {"name": ..., "kind": "chord",              "input": ..., "error": true}
    {"name": ..., "kind": "numeric",            "input": ..., "result": <numeric_model>}
    {"name": ..., "kind": "numeric",            "input": ..., "error": true}
    {"name": ..., "kind": "numeric_from_chord", "key_root": ..., "chord": ...,
                  "substitution": ..., "result": <attrs_dict>}
    {"name": ..., "kind": "numeric_from_chord", ..., "error": true}

Usage (from tonalis root):
    source .venv/bin/activate
    python conformance/music-dsl/fuzz/oracle.py
"""

import json
import sys
from pathlib import Path

from music_dsl.domain.static import Notes
from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.numeric_chord import NumericChord
from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
from music_dsl.serialize import serialize_chord, serialize_numeric_chord, _serialize_chord_attrs

HERE = Path(__file__).resolve().parent
INPUTS = HERE / "inputs.json"
OUT = HERE / "python_out.json"


def _run_chord(record: dict) -> dict:
    inp = record["input"]
    try:
        model = serialize_chord(Chord(inp))
        return {"result": {"chord": model}}
    except Exception:
        return {"error": True}


def _run_numeric(record: dict) -> dict:
    inp = record["input"]
    try:
        nc = NumericChord.from_chord_string(inp)
        model = serialize_numeric_chord(nc)
        return {"result": {"numeric": model}}
    except Exception:
        return {"error": True}


def _run_numeric_from_chord(record: dict) -> dict:
    key_root = record["key_root"]
    chord_str = record["chord"]
    substitution = record["substitution"]
    try:
        attrs = NumericChord._from_chord(Notes(key_root), Chord(chord_str), substitution)
        model = _serialize_chord_attrs(attrs)
        return {"result": {"numeric": model}}
    except Exception:
        return {"error": True}


RUNNERS = {
    "chord":              _run_chord,
    "numeric":            _run_numeric,
    "numeric_from_chord": _run_numeric_from_chord,
}


def run() -> list[dict]:
    records = json.loads(INPUTS.read_text())
    outputs = []
    errors = 0

    for i, record in enumerate(records):
        kind = record["kind"]
        name = f"fuzz/{kind}/{i:04d}"

        runner = RUNNERS.get(kind)
        if runner is None:
            print(f"WARNING: unknown kind {kind!r} at index {i}", file=sys.stderr)
            continue

        outcome = runner(record)
        entry: dict = {"name": name, "kind": kind}

        # copy input keys
        if kind == "chord":
            entry["input"] = record["input"]
        elif kind == "numeric":
            entry["input"] = record["input"]
        elif kind == "numeric_from_chord":
            entry["key_root"] = record["key_root"]
            entry["chord"] = record["chord"]
            entry["substitution"] = record["substitution"]

        if "error" in outcome:
            entry["error"] = True
            errors += 1
        else:
            entry["result"] = outcome["result"]

        outputs.append(entry)

    return outputs


if __name__ == "__main__":
    outputs = run()
    OUT.write_text(json.dumps(outputs, indent=2) + "\n")

    counts: dict[str, dict[str, int]] = {}
    for o in outputs:
        kind = o["kind"]
        bucket = "error" if o.get("error") else "ok"
        counts.setdefault(kind, {}).setdefault(bucket, 0)
        counts[kind][bucket] += 1

    print(f"Oracle recorded {len(outputs)} outputs -> {OUT}")
    for kind, buckets in sorted(counts.items()):
        ok = buckets.get("ok", 0)
        err = buckets.get("error", 0)
        print(f"  {kind}: {ok} ok, {err} error")
