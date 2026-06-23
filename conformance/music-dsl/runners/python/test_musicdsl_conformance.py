import json
import subprocess
import sys
from pathlib import Path

RUN_PY = Path(__file__).resolve().parent / "run.py"
CASES = Path(__file__).resolve().parents[2] / "cases"
EXPECTED_CASE_COUNT = 115  # 19 intervals + 25 notes + 7 scale_degrees + 64 encode (3 scales + 35 encoding + 8 strip + 6 semitones + 12 scan_scale)


def test_musicdsl_conformance_passes():
    result = subprocess.run([sys.executable, str(RUN_PY)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_conformance_case_count_is_frozen():
    # Frozen-count guard: a silently dropped/duplicated case (here or later in the
    # TS/Rust port runners) fails loudly instead of passing. NOTE this is STRONGER than
    # dsl-core's guard, which counts files; this counts individual cases, so a case
    # dropped from within a file is also caught. Port runners should match this (count
    # cases, not files).
    actual = sum(len(json.loads(f.read_text())) for f in CASES.rglob("*.json"))
    assert actual == EXPECTED_CASE_COUNT, f"case count drifted: {actual} != {EXPECTED_CASE_COUNT}"
