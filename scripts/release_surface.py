#!/usr/bin/env python3
"""The release surface: every place the version is written, and every place it is published.

One version drives six published artifacts across three registries, and it is
written into sixteen authored locations in four file formats. This module is the
single registry of both sets; the release scripts and workflows read it rather
than re-deriving paths, so adding a port or a lockfile is a one-line change here.

Writers are surgical (targeted line rewrites, not format round-trips) so that
rewriting the current version is byte-identical and generated lockfiles are never
reflowed.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parent.parent

USER_AGENT = "tonalis-release-check (+https://github.com/drycode/tonalis)"

# ---------------------------------------------------------------- semver

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

BUMPS = ("major", "minor", "patch")


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse a plain MAJOR.MINOR.PATCH version.

    Pre-release and build metadata are rejected: the six registries publish one
    immutable version per release and nothing here knows how to order `1.0.0-rc1`.
    """
    match = _SEMVER.match(version)
    if not match:
        raise ValueError(f"not a plain MAJOR.MINOR.PATCH version: {version!r}")
    major, minor, patch = (int(group) for group in match.groups())
    return major, minor, patch


def next_versions(previous: str) -> dict[str, str]:
    """The three versions that may legally follow `previous`."""
    major, minor, patch = parse_version(previous)
    return {
        "major": f"{major + 1}.0.0",
        "minor": f"{major}.{minor + 1}.0",
        "patch": f"{major}.{minor}.{patch + 1}",
    }


def bump_kind(previous: str, candidate: str) -> str:
    """Classify `candidate` as a major/minor/patch step over `previous`.

    Raises ValueError for anything that is not exactly one step: an unchanged
    version, a downgrade, or a skip such as 0.1.1 -> 0.1.5.
    """
    legal = next_versions(previous)
    parse_version(candidate)
    for kind, version in legal.items():
        if candidate == version:
            return kind
    raise ValueError(
        f"{candidate!r} is not a single semver step from {previous!r}; "
        f"expected one of {', '.join(legal[kind] for kind in BUMPS)}"
    )


# ---------------------------------------------------------------- slot readers/writers


def _table_bounds(lines: list[str], table: str) -> tuple[int, int]:
    """Half-open line range of the body of TOML table `[table]`."""
    start: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == f"[{table}]":
            start = index + 1
            continue
        if start is not None and stripped.startswith("[") and stripped.endswith("]"):
            return start, index
    if start is None:
        raise KeyError(f"no [{table}] table")
    return start, len(lines)


def _toml_key(table: str, key: str) -> tuple[Callable, Callable]:
    pattern = re.compile(rf'^(\s*{re.escape(key)}\s*=\s*")([^"]+)(")')

    def locate(text: str) -> tuple[list[str], int, re.Match]:
        lines = text.splitlines(keepends=True)
        low, high = _table_bounds([line.rstrip("\n") for line in lines], table)
        for index in range(low, high):
            match = pattern.match(lines[index])
            if match:
                return lines, index, match
        raise KeyError(f"no {key!r} in [{table}]")

    def read(text: str) -> str:
        return locate(text)[2].group(2)

    def write(text: str, version: str) -> str:
        lines, index, match = locate(text)
        lines[index] = f"{match.group(1)}{version}{match.group(3)}{lines[index][match.end(3):]}"
        return "".join(lines)

    return read, write


def _regex_capture(pattern: str) -> tuple[Callable, Callable]:
    compiled = re.compile(pattern)

    def locate(text: str) -> re.Match:
        match = compiled.search(text)
        if not match:
            raise KeyError(f"no match for {pattern!r}")
        return match

    def read(text: str) -> str:
        return locate(text).group("version")

    def write(text: str, version: str) -> str:
        low, high = locate(text).span("version")
        return text[:low] + version + text[high:]

    return read, write


def _json_key(*keys: str) -> tuple[Callable, Callable]:
    def read(text: str) -> str:
        node = json.loads(text)
        for key in keys:
            node = node[key]
        return node

    def write(text: str, version: str) -> str:
        document = json.loads(text)
        node = document
        for key in keys[:-1]:
            node = node[key]
        node[keys[-1]] = version
        return json.dumps(document, indent=2, ensure_ascii=False) + "\n"

    return read, write


def _lock_package(crate: str) -> tuple[Callable, Callable]:
    name_pattern = re.compile(r'^name\s*=\s*"([^"]+)"')
    version_pattern = re.compile(r'^(version\s*=\s*")([^"]+)(")')

    def locate(text: str) -> tuple[list[str], int, re.Match]:
        lines = text.splitlines(keepends=True)
        current: str | None = None
        for index, line in enumerate(lines):
            named = name_pattern.match(line)
            if named:
                current = named.group(1)
                continue
            versioned = version_pattern.match(line)
            if versioned and current == crate:
                return lines, index, versioned
        raise KeyError(f"no [[package]] {crate!r}")

    def read(text: str) -> str:
        return locate(text)[2].group(2)

    def write(text: str, version: str) -> str:
        lines, index, match = locate(text)
        lines[index] = f"{match.group(1)}{version}{match.group(3)}{lines[index][match.end(3):]}"
        return "".join(lines)

    return read, write


# ---------------------------------------------------------------- the surface


@dataclass(frozen=True)
class Slot:
    """One authored location holding the version."""

    path: str
    label: str
    group: str
    _read: Callable[[str], str]
    _write: Callable[[str, str], str]

    @property
    def name(self) -> str:
        return f"{self.path}:{self.label}"

    def read_text(self, text: str) -> str:
        """Read this slot out of file contents supplied by the caller."""
        return self._read(text)

    def read(self, root: Path = ROOT) -> str:
        return self.read_text((root / self.path).read_text())

    def write(self, version: str, root: Path = ROOT) -> bool:
        """Set this slot to `version`; True if the file changed."""
        target = root / self.path
        before = target.read_text()
        after = self._write(before, version)
        if after == before:
            return False
        target.write_text(after)
        return True


def _slot(path: str, label: str, group: str, io: tuple[Callable, Callable]) -> Slot:
    return Slot(path, label, group, io[0], io[1])


SLOTS: tuple[Slot, ...] = (
    # ---- package manifests: what each registry publishes as its version
    _slot("music-dsl/python/pyproject.toml", "project.version", "manifest", _toml_key("project", "version")),
    _slot("music-dsl/rust/Cargo.toml", "package.version", "manifest", _toml_key("package", "version")),
    _slot("music-dsl/ts/package.json", "version", "manifest", _json_key("version")),
    _slot("tonalis/python/pyproject.toml", "project.version", "manifest", _toml_key("project", "version")),
    _slot("tonalis/rust/Cargo.toml", "package.version", "manifest", _toml_key("package", "version")),
    _slot("tonalis/ts/package.json", "version", "manifest", _json_key("version")),
    # ---- internal pins: tonalis depends on the theory library at the same version
    _slot(
        "tonalis/python/pyproject.toml",
        "dependencies.tonalis-music-dsl",
        "pin",
        _regex_capture(r"tonalis-music-dsl==(?P<version>[0-9][0-9A-Za-z.\-+]*)"),
    ),
    _slot(
        "tonalis/rust/Cargo.toml",
        "dependencies.music_dsl.version",
        "pin",
        _regex_capture(r'(?m)^music_dsl\s*=\s*\{[^\n]*?version\s*=\s*"(?P<version>[^"]+)"'),
    ),
    # ---- lockfiles: committed, so they drift silently unless checked
    _slot("music-dsl/rust/Cargo.lock", "package.tonalis-music-dsl", "lock", _lock_package("tonalis-music-dsl")),
    _slot("music-dsl/ts/package-lock.json", "version", "lock", _json_key("version")),
    _slot("music-dsl/ts/package-lock.json", 'packages."".version', "lock", _json_key("packages", "", "version")),
    _slot("tonalis/rust/Cargo.lock", "package.tonalis", "lock", _lock_package("tonalis")),
    _slot("tonalis/rust/Cargo.lock", "package.tonalis-music-dsl", "lock", _lock_package("tonalis-music-dsl")),
    _slot("tonalis/ts/package-lock.json", "version", "lock", _json_key("version")),
    _slot("tonalis/ts/package-lock.json", 'packages."".version', "lock", _json_key("packages", "", "version")),
    _slot(
        "tonalis/ts/package-lock.json",
        'packages."../../music-dsl/ts".version',
        "lock",
        _json_key("packages", "../../music-dsl/ts", "version"),
    ),
)


def read_surface(root: Path = ROOT) -> dict[str, str]:
    """Every slot's current version, keyed by `path:label`."""
    return {slot.name: slot.read(root) for slot in SLOTS}


def current_version(root: Path = ROOT) -> str:
    """The single version the surface agrees on; raises if it disagrees."""
    versions = read_surface(root)
    distinct = sorted(set(versions.values()))
    if len(distinct) != 1:
        raise ValueError(f"release surface disagrees on version: {distinct}")
    return distinct[0]


def write_surface(version: str, root: Path = ROOT) -> list[str]:
    """Set every slot to `version`; returns the paths that changed."""
    parse_version(version)
    changed: list[str] = []
    for slot in SLOTS:
        if slot.write(version, root) and slot.path not in changed:
            changed.append(slot.path)
    return changed


# ---------------------------------------------------------------- published artifacts


@dataclass(frozen=True)
class Artifact:
    """One published package: a registry plus the name it is published under."""

    registry: str
    name: str
    slug: str

    def url(self, version: str) -> str:
        quoted = urllib.parse.quote(self.name, safe="")
        if self.registry == "pypi":
            return f"https://pypi.org/pypi/{quoted}/{version}/json"
        if self.registry == "npm":
            return f"https://registry.npmjs.org/{quoted}/{version}"
        if self.registry == "crates":
            return f"https://crates.io/api/v1/crates/{quoted}/{version}"
        raise ValueError(f"unknown registry {self.registry!r}")

    def describe(self) -> str:
        return f"{self.registry}:{self.name}"


ARTIFACTS: tuple[Artifact, ...] = (
    Artifact("pypi", "tonalis-music-dsl", "pypi_music_dsl"),
    Artifact("pypi", "tonalis", "pypi_tonalis"),
    Artifact("npm", "@tonalis/music-dsl", "npm_music_dsl"),
    Artifact("npm", "tonalis", "npm_tonalis"),
    Artifact("crates", "tonalis-music-dsl", "crates_music_dsl"),
    Artifact("crates", "tonalis", "crates_tonalis"),
)


def http_status(url: str, timeout: float = 30.0) -> int:
    """GET `url` and return its status, mapping HTTP errors to their code."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def is_published(
    artifact: Artifact,
    version: str,
    fetch: Callable[[str], int] = http_status,
) -> bool:
    """Whether `version` of `artifact` already exists in its registry.

    Anything other than 200 or 404 raises: treating an outage or a rate limit as
    "absent" would publish over a live release, and as "present" would silently
    skip publishing it.
    """
    status = fetch(artifact.url(version))
    if status == 200:
        return True
    if status == 404:
        return False
    raise RuntimeError(f"{artifact.describe()} {version}: unexpected HTTP {status}")


def publication_state(
    version: str,
    artifacts: Iterable[Artifact] = ARTIFACTS,
    fetch: Callable[[str], int] = http_status,
) -> dict[str, bool]:
    """Presence of `version` for each artifact, keyed by slug."""
    return {artifact.slug: is_published(artifact, version, fetch) for artifact in artifacts}
