"""Pytest wrapper: subprocess-invoke the dsl-core conformance runner and assert exit 0.

Keeps the dsl-core conformance suite (95 cases, ast/findings) gated by local ``pytest`` and CI.
The runner (``run.py``) loads ``conformance/dsl-core/cases/`` and asserts against the ``tonalis``
reference; this wrapper just runs it and surfaces its output on failure.
"""

import subprocess
import sys
from pathlib import Path

RUN_PY = Path(__file__).resolve().parent / "run.py"


def test_tonalis_conformance():
    r = subprocess.run(
        [sys.executable, str(RUN_PY)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
