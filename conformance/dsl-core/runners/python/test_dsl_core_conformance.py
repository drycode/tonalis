"""Pytest wrapper: subprocess-invoke the dsl-core conformance runner and assert exit 0.

Keeps the dsl-core conformance suite (95 cases, ast/findings) gated by local ``pytest`` and CI.
The runner (``run.py``) loads ``conformance/dsl-core/cases/`` and asserts against the ``tonalis``
reference; this wrapper just runs it and surfaces its output on failure.
"""

import subprocess
import sys
from pathlib import Path

RUN_PY = Path(__file__).resolve().parent / "run.py"
# runner: <repo>/conformance/dsl-core/runners/python/run.py  ->  cases at parents[2]/cases
_CASES_DIR = Path(__file__).resolve().parents[2] / "cases"

# Ledger M2/M3: the dsl-core conformance corpus is frozen at this many cases. A silently-dropped
# (or accidentally-duplicated) case must fail loudly here rather than quietly shrinking coverage
# across the three ports. Bump this number deliberately when cases are added.
EXPECTED_CASE_COUNT = 255


def test_tonalis_conformance():
    r = subprocess.run(
        [sys.executable, str(RUN_PY)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_conformance_case_count_is_frozen():
    """A dropped/duplicated conformance case must fail loudly (ledger M2/M3)."""
    actual = sum(1 for _ in _CASES_DIR.rglob("*.json"))
    assert actual == EXPECTED_CASE_COUNT, (
        f"dsl-core conformance case count drifted: expected {EXPECTED_CASE_COUNT}, "
        f"found {actual} under {_CASES_DIR}"
    )
