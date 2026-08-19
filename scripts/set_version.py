#!/usr/bin/env python3
"""Set the release version across every authored location.

Every merge to main publishes, so every pull request declares its version. The
version lives in sixteen places across four file formats (see
`scripts/release_surface.py`); editing them by hand is how lockfiles and internal
pins drift out of step. Run this instead.

Usage:
    set_version.py 0.2.0        # set an explicit version
    set_version.py --bump minor # step the current version

Then commit the result. `version-gate.yml` verifies it on the pull request and
`release.yml` publishes it on merge.
"""

from __future__ import annotations

import argparse
import sys

from release_surface import BUMPS, current_version, next_versions, write_surface


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("version", nargs="?", help="explicit MAJOR.MINOR.PATCH version")
    target.add_argument("--bump", choices=BUMPS, help="step the current version")
    args = parser.parse_args(argv[1:])

    previous = current_version()
    version = args.version or next_versions(previous)[args.bump]

    if version == previous:
        print(f"error: already at {version}; every merge must ship a new version", file=sys.stderr)
        return 1

    changed = write_surface(version)
    print(f"{previous} -> {version}")
    for path in changed:
        print(f"  updated {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
