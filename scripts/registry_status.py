#!/usr/bin/env python3
"""Report which of the six artifacts already exist at a version.

Registry versions are immutable, so both gates need this fact rather than a
guess. The pull request gate uses it twice: the declared version must be absent
everywhere (nothing to collide with), and the version on main must be present
everywhere (no half-published release to stack on top of). The release workflow
uses it to publish only what is missing — which makes a partially failed release
repairable by rerunning it — and again at the end to prove the release landed
before tagging it.

Usage:
    registry_status.py 0.1.2 --require-absent
    registry_status.py 0.1.1 --require-present
    registry_status.py 0.1.2 --github-output
    registry_status.py 0.1.2 --require-present --retries 5   # allow for propagation

Exit 0 when the requested condition holds; 1 otherwise.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from release_surface import ARTIFACTS, is_published


def survey(version: str) -> dict[str, bool]:
    return {artifact.slug: is_published(artifact, version) for artifact in ARTIFACTS}


def report(version: str, present: dict[str, bool]) -> None:
    for artifact in ARTIFACTS:
        state = "published" if present[artifact.slug] else "absent"
        print(f"{state:<10} {artifact.describe()} {version}", flush=True)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version")
    parser.add_argument(
        "--require-absent",
        action="store_true",
        help="fail if any artifact already exists at this version",
    )
    parser.add_argument(
        "--require-present",
        action="store_true",
        help="fail unless every artifact exists at this version",
    )
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="emit publish_<slug> flags for the release workflow",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=0,
        help="re-survey this many times while --require-present is unmet (registry propagation)",
    )
    parser.add_argument("--delay", type=float, default=15.0, help="seconds between retries")
    args = parser.parse_args(argv[1:])
    version = args.version.lstrip("v")

    present = survey(version)
    for remaining in range(args.retries, 0, -1):
        if not args.require_present or all(present.values()):
            break
        missing = [slug for slug, exists in present.items() if not exists]
        print(f"waiting {args.delay:g}s for {', '.join(missing)} ({remaining} left)", flush=True)
        time.sleep(args.delay)
        present = survey(version)

    report(version, present)

    if args.github_output:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
            for slug, exists in present.items():
                handle.write(f"publish_{slug}={'false' if exists else 'true'}\n")
            handle.write(f"any_pending={'true' if not all(present.values()) else 'false'}\n")

    if args.require_absent and any(present.values()):
        taken = ", ".join(slug for slug, exists in present.items() if exists)
        print(
            f"error: version {version} is already published ({taken}); "
            "registry versions are immutable, so pick the next version",
            file=sys.stderr,
        )
        return 1

    if args.require_present and not all(present.values()):
        missing = ", ".join(slug for slug, exists in present.items() if not exists)
        print(
            f"error: release {version} is incomplete ({missing} never published); "
            "rerun its release workflow — the publish jobs skip whatever already landed",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
