#!/usr/bin/env python3
"""Assert every published manifest agrees on version — and matches the release tag.

Six artifacts (tonalis + tonalis-music-dsl, each in Python/Rust/TS) carry a
hand-synced version across three file formats. A tag that disagrees with any of
them means a partial or mismatched publish to registries where versions are
immutable. The release workflow runs this in a guard job before anything builds.

Usage:
    check_release_version.py            # assert the six manifests agree
    check_release_version.py v0.1.1     # also assert they equal this tag/version

Exit 0 on agreement (and match, if a version was given); 1 otherwise.
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# path -> (format, key path to the version string)
MANIFESTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "tonalis/python/pyproject.toml": ("toml", ("project", "version")),
    "music-dsl/python/pyproject.toml": ("toml", ("project", "version")),
    "tonalis/rust/Cargo.toml": ("toml", ("package", "version")),
    "music-dsl/rust/Cargo.toml": ("toml", ("package", "version")),
    "tonalis/ts/package.json": ("json", ("version",)),
    "music-dsl/ts/package.json": ("json", ("version",)),
}


def read_version(rel: str, kind: str, keypath: tuple[str, ...]) -> str:
    text = (ROOT / rel).read_text()
    obj = tomllib.loads(text) if kind == "toml" else json.loads(text)
    for key in keypath:
        obj = obj[key]
    if not isinstance(obj, str):
        raise TypeError(f"{rel}: version is {type(obj).__name__}, not a string")
    return obj


def manifest_versions() -> dict[str, str]:
    return {rel: read_version(rel, kind, kp) for rel, (kind, kp) in MANIFESTS.items()}


def main(argv: list[str]) -> int:
    expected = argv[1].lstrip("v") if len(argv) > 1 else None
    versions = manifest_versions()

    for rel, v in versions.items():
        mark = "" if expected is None else ("  ✓" if v == expected else "  ✗ MISMATCH")
        print(f"{v:<10} {rel}{mark}")

    distinct = set(versions.values())
    if len(distinct) != 1:
        print(f"error: manifests disagree on version: {sorted(distinct)}", file=sys.stderr)
        return 1

    only = distinct.pop()
    if expected is not None and only != expected:
        print(
            f"error: tag version {expected!r} does not match manifest version {only!r}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
