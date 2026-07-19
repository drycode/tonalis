"""Import-boundary guard — ships WITH tonalis (spec §7).

Statically proves the dependency invariant by AST-scanning each PACKAGE module's imports against an
allow-LIST (whitelist, not blacklist — a name-prefix blacklist can be slipped by a string-built
import like ``import_module("for" + "bidden")``; an allow-list cannot):

  - ``tonalis/**``       may import ONLY stdlib + other ``tonalis`` submodules + ``music_dsl``,
                         the theory library it stands on. The dependency rule is one-way
                         (tonalis -> music_dsl): tonalis MAY import music_dsl (e.g. the chord
                         validator delegates to ``music_dsl ... Chord``), but ``music_dsl`` must
                         NEVER import tonalis. Nothing else outside (stdlib + tonalis + music_dsl)
                         is permitted.

The pure language core has no other runtime dependency. Notation-format codecs are separate adapter
packages built on top of this core (not shipped here); this guard is what keeps the core free of any
reach into such an adapter.

ANY ``importlib.import_module`` / ``__import__`` call is flagged as a violation outright (a dynamic
import is opaque to the allow-list and is exactly how a blacklist gets slipped). Pure AST walk — no
execution, so it can't be fooled by lazy/conditional imports.

The guard travels with the tonalis OSS package so the purity invariant ships with the core. NEGATIVE
tests (``test_guard_bites_on_*``) prove the guard FAILS when a forbidden import is present, scanning
synthetic in-memory modules so the real tonalis package is never poisoned.
"""

import ast
import sys
from pathlib import Path

import pytest

# package root: <root>/python/tests/test_boundary.py -> parents[1] = <root>/python
_PYTHON_ROOT = Path(__file__).resolve().parents[1]
_STDLIB = set(sys.stdlib_module_names)

# Top-level import names allowed beyond stdlib for the language runtime.
_DSL_CORE_EXTRA = {"tonalis", "music_dsl"}

_DYNAMIC_IMPORT_NAMES = {"import_module", "__import__"}


def _top_name(dotted: str) -> str:
    return dotted.split(".", 1)[0]


def _resolve_relative(level: int, module: str | None, names, module_pkg: str | None):
    """Resolve a relative import to absolute dotted targets against ``module_pkg``.

    ``module_pkg`` is the dotted package the importing module LIVES IN (e.g. ``tonalis.foo``).
    A ``from .x import y`` / ``from ..a import b`` is resolved like CPython: drop ``level-1``
    trailing components of the package, then append ``module`` (and, when ``module`` is None — a
    bare ``from . import x`` / ``from .. import y`` — append each imported member name).

    Yields absolute dotted target strings. If resolution would climb ABOVE the top package
    (``level`` exceeds the package depth), yields the sentinel ``"<escapes-package>"`` so the
    caller flags it (a relative import that escapes the package is a boundary breach).
    """
    if module_pkg is None:
        # No package context (synthetic source): we cannot resolve, but a relative import that
        # climbs (level>1, or level==1 with no module of its own that stays put) is still suspect.
        # Be conservative: a same-package `from . import x` is allowed; anything that climbs out
        # (level>=2) is flagged as an escape.
        if level >= 2:
            yield "<escapes-package>"
        return
    parts = module_pkg.split(".")
    # `from . import x` resolves within `module_pkg`; each extra level drops one package component.
    drop = level - 1
    if drop > len(parts):
        yield "<escapes-package>"
        return
    base = parts[: len(parts) - drop] if drop else parts
    if not base:
        # climbed all the way to (or above) the top — escapes the package
        yield "<escapes-package>"
        return
    base_dotted = ".".join(base)
    if module:
        yield f"{base_dotted}.{module}"
    else:
        # `from .. import a, b` -> targets are base.a, base.b
        for alias in names:
            yield f"{base_dotted}.{alias.name}"


def scan_imports(source: str, *, module_pkg: str | None = None):
    """Yield import facts from source AST:

      ('static', dotted_module)   — an absolute import target (every alias of `import a, b`, and
                                    every member of `from pkg import x, y` is yielded as pkg.x/pkg.y
                                    so member-surface imports are visible to the allow-list).
      ('dynamic', call_name)      — an importlib.import_module/__import__ call (forbidden outright).

    Relative imports (`from . import x`, `from ..a import b`) are resolved against ``module_pkg``
    (the dotted package the module lives in); an unresolvable / climbing target yields the sentinel
    ``"<escapes-package>"`` so the caller flags it.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # scan ALL aliases: `import os, some_adapter` must surface BOTH, not just names[0].
            for alias in node.names:
                yield ("static", alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # relative — resolve against the package and apply the same allow-list.
                for tgt in _resolve_relative(node.level, node.module, node.names, module_pkg):
                    yield ("static", tgt)
                continue
            if node.module is None:
                continue
            # absolute `from pkg.sub import a, b`: surface the module AND each member as a candidate
            # target (pkg.sub.a, pkg.sub.b) so a member-surface import (e.g. `from somepkg import x`)
            # is checked against the allow-list, not just the bare `node.module`.
            yield ("static", node.module)
            for alias in node.names:
                if alias.name == "*":
                    continue
                yield ("static", f"{node.module}.{alias.name}")
        elif isinstance(node, ast.Call):
            # flag importlib.import_module(...) and __import__(...) calls outright
            fn = node.func
            name = None
            if isinstance(fn, ast.Name):
                name = fn.id
            elif isinstance(fn, ast.Attribute):
                name = fn.attr
            if name in _DYNAMIC_IMPORT_NAMES:
                yield ("dynamic", name)


def check_source(source: str, *, extra_allowed: set, module_pkg: str | None = None):
    """Return a list of violation strings for one module's source ([] = clean).

    ``module_pkg`` is the dotted package the source lives in, used to resolve relative imports.
    """
    violations = []
    for kind, val in scan_imports(source, module_pkg=module_pkg):
        if kind == "dynamic":
            violations.append(f"dynamic import call `{val}(...)` is forbidden (opaque to the allow-list)")
            continue
        if val == "<escapes-package>":
            violations.append(
                "relative import escapes the package (climbs above its top-level) — forbidden"
            )
            continue
        top = _top_name(val)
        if top in _STDLIB:
            continue
        if top not in extra_allowed:
            violations.append(f"import `{val}` is outside the allow-list")
    return violations


def _package_modules(pkg_dir: Path, *, exclude_parts=()):
    """Every PACKAGE .py module under pkg_dir (NOT tests). Skips __pycache__ + excluded subdirs."""
    for p in sorted(pkg_dir.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        if any(part in exclude_parts for part in p.parts):
            continue
        yield p


def _module_pkg_of(path: Path, pkg_dir: Path) -> str:
    """Dotted package the module at ``path`` LIVES IN, rooted at ``pkg_dir`` (the top package).

    e.g. pkg_dir=.../tonalis, path=.../tonalis/sub/mod.py -> "tonalis.sub"
    (a package __init__.py is itself the package, so .../tonalis/sub/__init__.py -> "tonalis.sub").
    """
    top = pkg_dir.name
    rel = path.relative_to(pkg_dir)
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__.py":
        parts = parts[:-1]  # __init__ lives IN its own package
    else:
        parts = parts[:-1]  # a module lives in its parent package
    return ".".join([top, *parts]) if parts else top


def _check_package(pkg_dir: Path, *, extra_allowed: set, exclude_parts=()):
    failures = []
    for path in _package_modules(pkg_dir, exclude_parts=exclude_parts):
        src = path.read_text(encoding="utf-8")
        module_pkg = _module_pkg_of(path, pkg_dir)
        for v in check_source(src, extra_allowed=extra_allowed, module_pkg=module_pkg):
            failures.append(f"{path.relative_to(_PYTHON_ROOT)}: {v}")
    return failures


# ---------------------------------------------------------------------------------------------------
# Positive guards: the real packages must be clean.
# ---------------------------------------------------------------------------------------------------

def test_tonalis_imports_only_stdlib_and_self():
    """The language runtime imports nothing outside stdlib + itself + ``music_dsl``.

    The theory lib is a one-way dependency (tonalis -> music_dsl): tonalis MAY lean on it (the chord
    validator delegates to ``music_dsl ... Chord``), so ``music_dsl`` is in the allow-list;
    ``music_dsl`` must never reach back into tonalis.

    The offline ``tools/`` developer subpackage (the chord-oracle builder) is excluded here and
    checked separately by ``test_tonalis_tools_imports_only_self_and_stdlib``.
    """
    pkg = _PYTHON_ROOT / "tonalis"
    assert pkg.is_dir(), pkg
    failures = _check_package(pkg, extra_allowed=_DSL_CORE_EXTRA, exclude_parts=("tools",))
    assert not failures, "tonalis PURITY violated:\n" + "\n".join(failures)


def test_tonalis_tools_imports_only_self_and_stdlib():
    """The offline ``tonalis.tools`` developer subpackage. The chord-oracle builder imports only
    stdlib + ``tonalis`` (chord_grammar + the chords wrapper). The boundary scan is per-module and
    DIRECT-import only, so the wrapper's transitive ``music_dsl`` use is checked at its own module
    by the test above, not here."""
    tools = _PYTHON_ROOT / "tonalis" / "tools"
    if not tools.is_dir():
        pytest.skip(f"tonalis.tools not present at {tools} (offline tool dropped from the OSS lib)")
    failures = _check_package(tools, extra_allowed={"tonalis"})
    assert not failures, "tonalis.tools boundary violated:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------------------------------
# NEGATIVE tests: the guard must BITE on a forbidden import (proves it isn't a no-op).
# Scans synthetic in-memory sources — the real tonalis is NEVER poisoned.
# ---------------------------------------------------------------------------------------------------

def test_guard_bites_on_forbidden_import():
    # a tonalis-style module that illegally imports an out-of-tree package
    poisoned = "import some_adapter\nfrom tonalis.ast import LeadSheet\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA)
    assert any("some_adapter" in s for s in v), f"guard FAILED to flag `import some_adapter`: {v}"


def test_guard_bites_on_from_import_of_forbidden_package():
    poisoned = "from some_adapter.render import render\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA)
    assert any("some_adapter" in s for s in v), f"guard FAILED to flag forbidden from-import: {v}"


def test_guard_bites_on_dynamic_import():
    poisoned = "import importlib\nm = importlib.import_module('some' + '_adapter')\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA)
    assert any("dynamic import" in s for s in v), f"guard FAILED to flag dynamic import: {v}"


def test_guard_bites_on_dunder_import():
    poisoned = "x = __import__('some_adapter')\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA)
    assert any("dynamic import" in s for s in v), f"guard FAILED to flag __import__: {v}"


def test_guard_bites_on_multi_alias_import():
    # `import os, some_adapter`: the forbidden alias is NOT names[0], so a names[0]-only scanner
    # would wave it through. ALL aliases must be scanned.
    poisoned = "import os, some_adapter\nfrom tonalis.ast import LeadSheet\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA)
    assert any("some_adapter" in s for s in v), (
        f"guard FAILED to flag forbidden 2nd alias of `import os, some_adapter`: {v}"
    )


def test_guard_bites_on_from_import_of_member_surface():
    # the member-surface bypass: `from somepkg import forbidden_sub` pulls a member in — a
    # node.module-only scanner sees only the bare `somepkg` and waves it through. The member must
    # be checked too (here `somepkg` itself is already out of the allow-list, so both are flagged).
    poisoned = "from some_adapter import sub\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA)
    assert any("some_adapter" in s for s in v), (
        f"guard FAILED to flag `from some_adapter import sub`: {v}"
    )


def test_guard_bites_on_relative_import_that_escapes_package():
    # `from ..adapter import x` from a TOP-LEVEL module (`tonalis/x.py`, package = "tonalis")
    # climbs one level ABOVE `tonalis` — it escapes the package entirely. A naive guard that
    # unconditionally allowed any level>0 relative import would miss this.
    poisoned = "from ..adapter import render\nfrom tonalis.ast import LeadSheet\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA, module_pkg="tonalis")
    assert any("escapes the package" in s for s in v), (
        f"guard FAILED to flag a relative import that escapes the package: {v}"
    )
    # also: a deeper module climbing two levels above its top escapes too.
    deeper = "from ...other import x\n"
    v2 = check_source(deeper, extra_allowed=_DSL_CORE_EXTRA, module_pkg="tonalis.sub")
    assert any("escapes the package" in s for s in v2), (
        f"guard FAILED to flag a deep relative import escaping the package: {v2}"
    )


def test_guard_allows_within_package_relative_import():
    # the flip side: a same-package `from . import x` / `from .sib import y` stays allowed.
    ok = "from . import ast\nfrom .lint import lint\n"
    v = check_source(ok, extra_allowed=_DSL_CORE_EXTRA, module_pkg="tonalis")
    assert v == [], f"guard wrongly flagged a within-package relative import: {v}"


def test_guard_passes_clean_tonalis_source():
    # sanity: a clean module must produce ZERO violations (the guard isn't trivially always-failing)
    clean = "import re\nfrom tonalis.ast import LeadSheet\nfrom dataclasses import dataclass\n"
    assert check_source(clean, extra_allowed=_DSL_CORE_EXTRA) == []


def test_guard_allows_music_dsl_runtime_dep():
    # the production runtime dep the chord validator stands on is allowed from any module.
    ok = "from music_dsl.domain.chords import Chord\n"
    v = check_source(ok, extra_allowed=_DSL_CORE_EXTRA, module_pkg="tonalis")
    assert v == [], f"guard wrongly flagged the music_dsl runtime dep: {v}"


# ---------------------------------------------------------------------------------------------------
# Reverse-dependency guard: music_dsl must NOT import tonalis (one-way invariant).
# ---------------------------------------------------------------------------------------------------

def test_music_dsl_does_not_import_tonalis():
    """Rule: tonalis -> music_dsl is allowed; music_dsl -> tonalis is FORBIDDEN.

    AST-scan every module under music-dsl/python/music_dsl/** and assert that none imports a
    top-level name ``tonalis``.  This is the reverse of ``test_tonalis_imports_only_stdlib_and_self``;
    together they enforce the one-way dependency invariant both ways.
    """
    # music-dsl lives in a sibling directory one level above tonalis/python
    music_dsl_pkg = _PYTHON_ROOT.parents[1] / "music-dsl" / "python" / "music_dsl"
    if not music_dsl_pkg.is_dir():
        pytest.skip(
            f"music_dsl package not found at {music_dsl_pkg} "
            "(music-dsl submodule absent or not checked out)"
        )
    violations = []
    for path in _package_modules(music_dsl_pkg):
        src = path.read_text(encoding="utf-8")
        module_pkg = _module_pkg_of(path, music_dsl_pkg)
        for kind, val in scan_imports(src, module_pkg=module_pkg):
            if kind == "static" and _top_name(val) == "tonalis":
                violations.append(f"{path.relative_to(music_dsl_pkg.parent)}: imports `{val}`")
    assert not violations, (
        "music_dsl MUST NOT import tonalis (one-way invariant violated):\n"
        + "\n".join(violations)
    )
