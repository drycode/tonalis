"""Import-boundary guard — ships WITH tonalis (spec §7).

Statically proves the one-way dependency invariant by AST-scanning each PACKAGE module's imports
against an allow-LIST (whitelist, not blacklist — a name-prefix blacklist can be slipped by a
string-built import like ``import_module("SCRUBBED"+"Parser.cst")``; an allow-list cannot):

  - ``tonalis/**``       may import ONLY stdlib + other ``tonalis`` submodules. It is the PURE
                         language core and must depend on NOTHING outside itself.

The ``SCRUBBED``/``text_target`` adapter packages live in a separate (private) repository and are
not part of this standalone library; their boundary tests below ``pytest.skip`` here. The negative
guard tests still run against synthetic in-memory sources to prove the scanner itself bites.

ANY ``importlib.import_module`` / ``__import__`` call is flagged as a violation outright (a dynamic
import is opaque to the allow-list and is exactly how a blacklist gets slipped). Pure AST walk — no
execution, so it can't be fooled by lazy/conditional imports.

The guard travels with the tonalis OSS package so the purity invariant ships with the core. A NEGATIVE
test (``test_guard_bites_on_forbidden_import``) proves the guard FAILS when a forbidden import is
present, scanning a synthetic in-memory module so the real tonalis package is never poisoned.
"""

import ast
import sys
from pathlib import Path

import pytest

# package root: <root>/python/tests/test_boundary.py -> parents[1] = <root>/python
_PYTHON_ROOT = Path(__file__).resolve().parents[1]
_STDLIB = set(sys.stdlib_module_names)

# Per-package allow-lists of TOP-LEVEL import names beyond stdlib. Submodule-prefix entries (with a
# trailing-dot meaning) are handled by `_top_name`/`_extra_allowed` below.
_DSL_CORE_EXTRA = {"tonalis"}
_SCRUBBED = {"tonalis", "SCRUBBED", "SCRUBBED"}
_TEXT_TARGET_EXTRA = {"tonalis", "text_target"}

# The codec may ONLY reach these SCRUBBED surfaces (the iReal reader + the cst/SCRUBBED codec).
# Anything else under SCRUBBED (e.g. the old `SCRUBBED.dsl`) is forbidden even though the
# top-level name is allowed. `SCRUBBED.cst` is a PREFIX allow (the cst subpackage + its modules:
# cst.chart / cst.url / cst.encoder / cst.lexer); the others are exact.
_SCRUBBED = {
    "SCRUBBED",  # bare: the Tune reader (`from SCRUBBED import Tune`)
    "SCRUBBED.SCRUBBED",
}
_SCRUBBED = (
    "SCRUBBED.cst",  # the iReal CST codec subpackage (cst.chart/url/encoder/lexer)
)
# Forbidden SCRUBBED SUBPACKAGES — reached via either `import SCRUBBED.dsl` or the
# adapter-surface bypass `from SCRUBBED import dsl`. `dsl` is the OLD codec subpackage the split
# extracted into SCRUBBED; the codec must reach the reader/cst/SCRUBBED, never the old dsl codec.
_SCRUBBED = ("dsl",)

_DYNAMIC_IMPORT_NAMES = {"import_module", "__import__"}


def _top_name(dotted: str) -> str:
    return dotted.split(".", 1)[0]


def _resolve_relative(level: int, module: str | None, names, module_pkg: str | None):
    """Resolve a relative import to absolute dotted targets against ``module_pkg``.

    ``module_pkg`` is the dotted package the importing module LIVES IN (e.g. ``SCRUBBED.foo``).
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
                                    so adapter-surface members are visible to the allow-list).
      ('dynamic', call_name)      — an importlib.import_module/__import__ call (forbidden outright).

    Relative imports (`from . import x`, `from ..a import b`) are resolved against ``module_pkg``
    (the dotted package the module lives in); an unresolvable / climbing target yields the sentinel
    ``"<escapes-package>"`` so the caller flags it.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # scan ALL aliases: `import os, SCRUBBED` must surface BOTH, not just names[0].
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
            # target (pkg.sub.a, pkg.sub.b) so an adapter-surface member (e.g. the `dsl` codec
            # subpackage in `from SCRUBBED import dsl`) is checked against the allow-list, not
            # just the bare `node.module`.
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


def _SCRUBBED(val: str) -> bool:
    # Forbidden subpackages (the old `SCRUBBED.dsl` codec) are rejected FIRST, before any allow:
    # this catches both `import SCRUBBED.dsl` and the member-bypass `from SCRUBBED import dsl`
    # (which the scanner surfaces as the dotted target `SCRUBBED.dsl`).
    for sub in _SCRUBBED:
        if val == f"SCRUBBED.{sub}" or val.startswith(f"SCRUBBED.{sub}."):
            return False
    if val in _SCRUBBED:
        return True
    if any(val == p or val.startswith(p + ".") for p in _SCRUBBED):
        return True
    # A bare member of the reader (`from SCRUBBED import Tune` -> target `SCRUBBED.Tune`)
    # that is NOT a forbidden subpackage is an ordinary symbol off the reader surface — allowed.
    # (Only known-forbidden subpackages are rejected; everything else off the bare reader is fine.)
    return val == "SCRUBBED" or val.startswith("SCRUBBED.")


def check_source(source: str, *, extra_allowed: set, codec_SCRUBBED: bool = False,
                 module_pkg: str | None = None):
    """Return a list of violation strings for one module's source ([] = clean).

    ``codec_SCRUBBED`` enables the codec's narrow SCRUBBED allow (reader + cst/SCRUBBED only).
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
            continue
        # SCRUBBED is allow-listed for the codec but only for the reader + cst/SCRUBBED surfaces.
        if top == "SCRUBBED":
            if not codec_SCRUBBED:
                violations.append(f"import `{val}` (SCRUBBED) is outside the allow-list")
            elif not _SCRUBBED(val):
                violations.append(
                    f"import `{val}` is not an allowed SCRUBBED codec surface "
                    f"(reader / SCRUBBED.cst / SCRUBBED.SCRUBBED only)"
                )
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

    e.g. pkg_dir=.../SCRUBBED, path=.../SCRUBBED/sub/mod.py -> "SCRUBBED.sub"
    (a package __init__.py is itself the package, so .../SCRUBBED/sub/__init__.py -> "SCRUBBED.sub").
    """
    top = pkg_dir.name
    rel = path.relative_to(pkg_dir)
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__.py":
        parts = parts[:-1]  # __init__ lives IN its own package
    else:
        parts = parts[:-1]  # a module lives in its parent package
    return ".".join([top, *parts]) if parts else top


def _check_package(pkg_dir: Path, *, extra_allowed: set, codec_SCRUBBED: bool = False,
                   exclude_parts=()):
    failures = []
    for path in _package_modules(pkg_dir, exclude_parts=exclude_parts):
        src = path.read_text(encoding="utf-8")
        module_pkg = _module_pkg_of(path, pkg_dir)
        for v in check_source(src, extra_allowed=extra_allowed,
                              codec_SCRUBBED=codec_SCRUBBED, module_pkg=module_pkg):
            failures.append(f"{path.relative_to(_PYTHON_ROOT)}: {v}")
    return failures


# ---------------------------------------------------------------------------------------------------
# Positive guards: the real packages must be clean.
# ---------------------------------------------------------------------------------------------------

def test_tonalis_imports_only_stdlib_and_self():
    """The PURE language runtime imports nothing outside itself + stdlib.

    The offline ``tools/`` developer subpackage (the conformance bless tool, which imports the iReal
    codec) is NOT shipped in this standalone library, so there is nothing to exclude here.
    """
    pkg = _PYTHON_ROOT / "tonalis"
    assert pkg.is_dir(), pkg
    failures = _check_package(pkg, extra_allowed=_DSL_CORE_EXTRA, exclude_parts=("tools",))
    assert not failures, "tonalis PURITY violated:\n" + "\n".join(failures)


def test_tonalis_tools_imports_only_dslcore_codec_and_stdlib():
    """The bless tool is the codec-direction consumer of both packages. It is intentionally NOT
    shipped in the standalone library (it imports the private iReal codec), so this skips."""
    tools = _PYTHON_ROOT / "tonalis" / "tools"
    if not tools.is_dir():
        pytest.skip(f"tonalis.tools not present at {tools} (offline tool dropped from the OSS lib)")
    failures = _check_package(tools, extra_allowed={"tonalis", "SCRUBBED"})
    assert not failures, "tonalis.tools boundary violated:\n" + "\n".join(failures)


def test_SCRUBBED():
    pkg = _PYTHON_ROOT.parent / "ireal-codec" / "python" / "SCRUBBED"
    if not pkg.is_dir():
        pytest.skip(f"SCRUBBED package not present at {pkg} (private repo, out of scope)")
    failures = _check_package(pkg, extra_allowed=_SCRUBBED, codec_SCRUBBED=True)
    assert not failures, "SCRUBBED boundary violated:\n" + "\n".join(failures)


def test_text_target_imports_only_dslcore_and_stdlib():
    pkg = _PYTHON_ROOT.parent / "text-target" / "text_target"
    if not pkg.is_dir():
        pytest.skip(f"text_target package not present at {pkg} (private repo, out of scope)")
    failures = _check_package(pkg, extra_allowed=_TEXT_TARGET_EXTRA)
    assert not failures, "text_target boundary violated:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------------------------------
# NEGATIVE test: the guard must BITE on a forbidden import (proves it isn't a no-op).
# Scans synthetic in-memory sources — the real tonalis is NEVER poisoned.
# ---------------------------------------------------------------------------------------------------

def test_guard_bites_on_forbidden_import():
    # a tonalis-style module that illegally imports an adapter
    poisoned = "import SCRUBBED\nfrom tonalis.ast import LeadSheet\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA)
    assert any("SCRUBBED" in s for s in v), f"guard FAILED to flag `import SCRUBBED`: {v}"


def test_guard_bites_on_from_import_of_adapter():
    poisoned = "from text_target.render import render\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA)
    assert any("text_target" in s for s in v), f"guard FAILED to flag adapter from-import: {v}"


def test_guard_bites_on_dynamic_import():
    poisoned = "import importlib\nm = importlib.import_module('SCRUBBED' + 'Parser.cst')\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA)
    assert any("dynamic import" in s for s in v), f"guard FAILED to flag dynamic import: {v}"


def test_guard_bites_on_dunder_import():
    poisoned = "x = __import__('SCRUBBED')\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA)
    assert any("dynamic import" in s for s in v), f"guard FAILED to flag __import__: {v}"


def test_guard_bites_on_codec_importing_text_target():
    # the adapter-vs-adapter rule: SCRUBBED must not see text_target
    poisoned = "from tonalis.ast import LeadSheet\nimport text_target\n"
    v = check_source(poisoned, extra_allowed=_SCRUBBED, codec_SCRUBBED=True)
    assert any("text_target" in s for s in v), f"guard FAILED to flag codec->text_target: {v}"


def test_guard_bites_on_codec_reaching_disallowed_SCRUBBED():
    # SCRUBBED is allow-listed, but only cst/SCRUBBED/the reader — not arbitrary internals
    poisoned = "from SCRUBBED.dsl.compiler import compile_dsl\n"
    v = check_source(poisoned, extra_allowed=_SCRUBBED, codec_SCRUBBED=True)
    assert any("SCRUBBED.dsl" in s for s in v), f"guard FAILED to flag disallowed surface: {v}"


def test_guard_bites_on_multi_alias_import():
    # (a) `import os, SCRUBBED`: the forbidden alias is NOT names[0], so a names[0]-only scanner
    # would wave it through. ALL aliases must be scanned.
    poisoned = "import os, SCRUBBED\nfrom tonalis.ast import LeadSheet\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA)
    assert any("SCRUBBED" in s for s in v), (
        f"guard FAILED to flag forbidden 2nd alias of `import os, SCRUBBED`: {v}"
    )


def test_guard_bites_on_from_import_of_dsl_codec_member():
    # (b) the adapter-surface bypass: `from SCRUBBED import dsl` pulls the FORBIDDEN
    # `SCRUBBED.dsl` codec subpackage in as a member — a node.module-only scanner sees only the
    # allowed bare `SCRUBBED` and waves it through. The member must be checked too.
    poisoned = "from SCRUBBED import dsl\n"
    v = check_source(poisoned, extra_allowed=_SCRUBBED, codec_SCRUBBED=True)
    assert any("SCRUBBED.dsl" in s for s in v), (
        f"guard FAILED to flag `from SCRUBBED import dsl` (forbidden codec subpackage): {v}"
    )


def test_guard_allows_from_import_of_legitimate_reader_surfaces():
    # the flip side of (b): the legitimate reader surfaces stay allowed (the member check must NOT
    # over-reject Tune / cst / SCRUBBED).
    ok = (
        "from SCRUBBED import Tune\n"
        "from SCRUBBED.cst.chart import Chart\n"
        "from SCRUBBED.SCRUBBED import SCRUBBED\n"
    )
    v = check_source(ok, extra_allowed=_SCRUBBED, codec_SCRUBBED=True)
    assert v == [], f"guard wrongly flagged a legitimate reader/cst/SCRUBBED surface: {v}"


def test_guard_bites_on_relative_import_that_escapes_package():
    # (c) `from ..adapter import x` from a TOP-LEVEL module (`tonalis/x.py`, package = "tonalis")
    # climbs one level ABOVE `tonalis` — it escapes the package entirely. The OLD guard
    # unconditionally allowed any level>0 relative import; this must now be caught.
    poisoned = "from ..adapter import render\nfrom tonalis.ast import LeadSheet\n"
    v = check_source(poisoned, extra_allowed=_DSL_CORE_EXTRA, module_pkg="tonalis")
    assert any("escapes the package" in s for s in v), (
        f"guard FAILED to flag a relative import that escapes the package: {v}"
    )
    # also: deeper module climbing two levels above its top escapes too.
    deeper = "from ...other import x\n"
    v2 = check_source(deeper, extra_allowed=_DSL_CORE_EXTRA, module_pkg="tonalis.sub")
    assert any("escapes the package" in s for s in v2), (
        f"guard FAILED to flag a deep relative import escaping the package: {v2}"
    )


def test_guard_allows_within_package_relative_import():
    # the flip side of (c): a same-package `from . import x` / `from .sib import y` stays allowed.
    ok = "from . import ast\nfrom .lint import lint\n"
    v = check_source(ok, extra_allowed=_DSL_CORE_EXTRA, module_pkg="tonalis")
    assert v == [], f"guard wrongly flagged a within-package relative import: {v}"


def test_guard_passes_clean_tonalis_source():
    # sanity: a clean module must produce ZERO violations (the guard isn't trivially always-failing)
    clean = "import re\nfrom tonalis.ast import LeadSheet\nfrom dataclasses import dataclass\n"
    assert check_source(clean, extra_allowed=_DSL_CORE_EXTRA) == []
