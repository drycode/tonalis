#!/usr/bin/env python3
"""Assert every authored location agrees on the version.

Six artifacts carry one hand-synced version across four file formats, plus two
internal pins and four committed lockfiles. Disagreement means a partial or
mismatched publish to registries where versions are immutable, so both the pull
request gate and the release guard run this before anything builds.

Usage:
    check_release_version.py            # assert the surface agrees
    check_release_version.py 0.1.2      # also assert it equals this version
    check_release_version.py --print    # print the agreed version, nothing else

Exit 0 on agreement (and match, if a version was given); 1 otherwise.
"""

from __future__ import annotations

import sys

from release_surface import SLOTS, read_surface


def main(argv: list[str]) -> int:
    args = [arg for arg in argv[1:] if arg != "--print"]
    quiet = "--print" in argv[1:]
    expected = args[0].lstrip("v") if args else None

    versions = read_surface()
    distinct = sorted(set(versions.values()))

    if not quiet:
        for group in ("manifest", "pin", "lock"):
            print(f"-- {group}")
            for slot in SLOTS:
                if slot.group != group:
                    continue
                found = versions[slot.name]
                mark = "" if expected is None else ("  ok" if found == expected else "  MISMATCH")
                print(f"   {found:<10} {slot.name}{mark}")

    if len(distinct) != 1:
        print(f"error: release surface disagrees on version: {distinct}", file=sys.stderr)
        print("hint: run scripts/set_version.py to rewrite every location", file=sys.stderr)
        return 1

    only = distinct[0]
    if expected is not None and only != expected:
        print(
            f"error: expected version {expected!r} but the surface says {only!r}",
            file=sys.stderr,
        )
        return 1

    if quiet:
        print(only)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
