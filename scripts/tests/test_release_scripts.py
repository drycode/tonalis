"""Tests for the release surface — the logic no other suite guards.

Six artifacts publish from one version written into sixteen authored locations,
and registry versions are immutable. The two failure modes worth defending are a
version that only *looks* synced (a lockfile left behind) and a presence check
that guesses when a registry misbehaves.
"""

from __future__ import annotations

import json
import shutil

import pytest

import release_surface as surface
from release_surface import ARTIFACTS, SLOTS, Artifact, bump_kind, is_published


# ---------------------------------------------------------------- semver steps


@pytest.mark.parametrize(
    "previous,candidate,expected",
    [
        ("0.1.1", "0.1.2", "patch"),
        ("0.1.1", "0.2.0", "minor"),
        ("0.1.1", "1.0.0", "major"),
        ("1.9.9", "1.9.10", "patch"),
        ("1.9.9", "1.10.0", "minor"),
        ("1.9.9", "2.0.0", "major"),
    ],
)
def test_legal_steps_are_classified(previous, candidate, expected):
    assert bump_kind(previous, candidate) == expected


@pytest.mark.parametrize(
    "previous,candidate",
    [
        ("0.1.1", "0.1.1"),  # unchanged: every merge must ship a new version
        ("0.1.1", "0.1.0"),  # downgrade
        ("0.1.1", "0.0.9"),  # downgrade across minor
        ("0.1.1", "0.1.5"),  # skipped patches
        ("0.1.1", "0.3.0"),  # skipped minor
        ("0.1.1", "2.0.0"),  # skipped major
        ("0.1.1", "1.1.0"),  # major bump without resetting minor
        ("0.1.1", "0.2.1"),  # minor bump without resetting patch
        ("0.1.1", "0.1.2-rc1"),  # pre-release: registries publish one version
        ("0.1.1", "0.1.2+build"),
        ("0.1.1", "01.1.2"),  # leading zero
        ("0.1.1", "v0.1.2"),  # tag spelling, not a version
    ],
)
def test_illegal_steps_are_rejected(previous, candidate):
    with pytest.raises(ValueError):
        bump_kind(previous, candidate)


# ---------------------------------------------------------------- the surface


def test_surface_covers_every_published_manifest():
    manifests = {slot.path for slot in SLOTS if slot.group == "manifest"}
    assert manifests == {
        "music-dsl/python/pyproject.toml",
        "music-dsl/rust/Cargo.toml",
        "music-dsl/ts/package.json",
        "tonalis/python/pyproject.toml",
        "tonalis/rust/Cargo.toml",
        "tonalis/ts/package.json",
    }
    assert len({slot.name for slot in SLOTS}) == len(SLOTS), "duplicate slot"


def test_repository_surface_agrees():
    """The checked-in tree is always releasable: one version, everywhere."""
    assert len(set(surface.read_surface().values())) == 1


@pytest.fixture
def tree(tmp_path):
    """A copy of just the files the surface touches, for write tests."""
    for path in {slot.path for slot in SLOTS}:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(surface.ROOT / path, target)
    return tmp_path


def test_rewriting_the_current_version_is_byte_identical(tree):
    """Writers must edit in place, not reflow generated lockfiles."""
    before = {path: (tree / path).read_bytes() for path in {slot.path for slot in SLOTS}}
    surface.write_surface(surface.current_version(tree), tree)
    for path, content in before.items():
        assert (tree / path).read_bytes() == content, f"{path} was reformatted"


def test_write_surface_moves_every_slot(tree):
    changed = surface.write_surface("9.8.7", tree)
    assert set(changed) == {slot.path for slot in SLOTS}
    assert surface.read_surface(tree) == {slot.name: "9.8.7" for slot in SLOTS}
    assert surface.current_version(tree) == "9.8.7"


def test_write_surface_updates_the_internal_pins(tree):
    surface.write_surface("2.3.4", tree)
    python = (tree / "tonalis/python/pyproject.toml").read_text()
    assert 'dependencies = ["tonalis-music-dsl==2.3.4"]' in python
    rust = (tree / "tonalis/rust/Cargo.toml").read_text()
    assert 'package = "tonalis-music-dsl", path = "../../music-dsl/rust", version = "2.3.4"' in rust


def test_write_surface_updates_the_linked_npm_dependency(tree):
    surface.write_surface("2.3.4", tree)
    lock = json.loads((tree / "tonalis/ts/package-lock.json").read_text())
    assert lock["packages"]["../../music-dsl/ts"]["version"] == "2.3.4"


def test_a_stale_lockfile_is_caught(tree):
    surface.write_surface("3.0.0", tree)
    stale = next(slot for slot in SLOTS if slot.path == "music-dsl/rust/Cargo.lock")
    stale.write("2.9.9", tree)
    with pytest.raises(ValueError, match="disagrees"):
        surface.current_version(tree)


def test_write_surface_rejects_a_non_semver_version(tree):
    with pytest.raises(ValueError):
        surface.write_surface("1.2", tree)


# ---------------------------------------------------------------- registries


def test_every_artifact_has_a_distinct_slug():
    assert len({artifact.slug for artifact in ARTIFACTS}) == len(ARTIFACTS) == 6


@pytest.mark.parametrize(
    "artifact,expected",
    [
        (
            Artifact("pypi", "tonalis-music-dsl", "pypi_music_dsl"),
            "https://pypi.org/pypi/tonalis-music-dsl/0.1.2/json",
        ),
        (
            Artifact("npm", "@tonalis/music-dsl", "npm_music_dsl"),
            "https://registry.npmjs.org/%40tonalis%2Fmusic-dsl/0.1.2",
        ),
        (
            Artifact("crates", "tonalis", "crates_tonalis"),
            "https://crates.io/api/v1/crates/tonalis/0.1.2",
        ),
    ],
)
def test_registry_urls(artifact, expected):
    assert artifact.url("0.1.2") == expected


def test_presence_maps_200_and_404():
    artifact = ARTIFACTS[0]
    assert is_published(artifact, "0.1.2", fetch=lambda url: 200) is True
    assert is_published(artifact, "0.1.2", fetch=lambda url: 404) is False


@pytest.mark.parametrize("status", [403, 429, 500, 502])
def test_presence_refuses_to_guess(status):
    """An outage must stop the release, not be read as absent or present."""
    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        is_published(ARTIFACTS[0], "0.1.2", fetch=lambda url: status)


def test_publication_state_is_keyed_by_slug():
    state = surface.publication_state("0.1.2", fetch=lambda url: 404)
    assert state == {artifact.slug: False for artifact in ARTIFACTS}
