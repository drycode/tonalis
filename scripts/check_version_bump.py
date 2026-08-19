#!/usr/bin/env python3
"""Assert this branch steps the version exactly once over its base branch.

Every merge to main publishes a release, so every pull request must declare a new
version, and it must be reachable in one step: PATCH+1, MINOR+1 with patch reset,
or MAJOR+1 with both reset. A skip (0.1.1 -> 0.1.5) or a downgrade is a typo, not
an intent, and versions are immutable once published.

Usage:
    check_version_bump.py origin/main [--github-output]

Emits `previous`, `version`, and `bump` as step outputs when asked. Exit 0 when
the step is legal; 1 otherwise.
"""

from __future__ import annotations

import os
import subprocess
import sys

from release_surface import ROOT, SLOTS, bump_kind, current_version, next_versions


def surface_at(ref: str) -> dict[str, str]:
    """Read every slot from a git ref rather than the working tree."""
    blobs: dict[str, str] = {}
    for slot in SLOTS:
        if slot.path not in blobs:
            blobs[slot.path] = subprocess.run(
                ["git", "show", f"{ref}:{slot.path}"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
    return {slot.name: slot.read_text(blobs[slot.path]) for slot in SLOTS}


def agreed(versions: dict[str, str], source: str) -> str:
    distinct = sorted(set(versions.values()))
    if len(distinct) != 1:
        raise SystemExit(f"error: {source} disagrees on version: {distinct}")
    return distinct[0]


def main(argv: list[str]) -> int:
    args = [arg for arg in argv[1:] if not arg.startswith("--")]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    ref = args[0]

    previous = agreed(surface_at(ref), ref)
    version = current_version()

    try:
        kind = bump_kind(previous, version)
    except ValueError as error:
        legal = next_versions(previous)
        print(f"error: {error}", file=sys.stderr)
        print(
            "hint: every merge publishes, so bump the version — "
            f"scripts/set_version.py --bump patch ({legal['patch']}), "
            f"--bump minor ({legal['minor']}), or --bump major ({legal['major']})",
            file=sys.stderr,
        )
        return 1

    print(f"{previous} -> {version} ({kind})")

    if "--github-output" in argv[1:]:
        output = os.environ["GITHUB_OUTPUT"]
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"previous={previous}\nversion={version}\nbump={kind}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
