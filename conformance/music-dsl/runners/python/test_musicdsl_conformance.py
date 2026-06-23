import json
import subprocess
import sys
from pathlib import Path

RUN_PY = Path(__file__).resolve().parent / "run.py"
CASES = Path(__file__).resolve().parents[2] / "cases"
EXPECTED_CASE_COUNT = 14  # 7 intervals + 5 notes + 2 scale_degrees


def test_musicdsl_conformance_passes():
    result = subprocess.run([sys.executable, str(RUN_PY)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_conformance_case_count_is_frozen():
    # Mirrors dsl-core's frozen-count guard: a silently dropped/duplicated case
    # (here or later in the TS/Rust port runners) fails loudly instead of passing.
    actual = sum(len(json.loads(f.read_text())) for f in CASES.rglob("*.json"))
    assert actual == EXPECTED_CASE_COUNT, f"case count drifted: {actual} != {EXPECTED_CASE_COUNT}"
