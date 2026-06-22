import re
from importlib.resources import files

from tonalis.lint import lint
from tonalis.parser import parse_dsl
from tonalis.chord_grammar import is_valid_chord


def _grammar_text() -> str:
    # GRAMMAR.md ships as tonalis package data (the language artifact); this drift test reads its own.
    return (files("tonalis") / "GRAMMAR.md").read_text(encoding="utf-8")


def _block(tag: str, text: str) -> str:
    m = re.search(rf"<!-- {tag} -->\s*```(.*?)```\s*<!-- /{tag} -->", text, re.DOTALL)
    assert m, f"GRAMMAR.md is missing the <!-- {tag} --> fenced block"
    return m.group(1).strip()


def _error_codes(dsl: str) -> set:
    """All error-severity finding codes the pure pipeline (parse + lint) raises for ``dsl``."""
    r = parse_dsl(dsl)
    extra = lint(r.chart) if r.chart else []
    return {f.code for f in (r.findings + extra) if f.severity == "error"}


def test_grammar_md_is_packaged_and_loadable():
    text = _grammar_text()
    assert "iReal DSL v1" in text


def test_every_documented_valid_chord_passes_parser():
    tokens = [
        t for t in _block("valid-chords", _grammar_text()).splitlines() if t.strip()
    ]
    assert tokens, "no valid-chord examples found"
    bad = [t for t in tokens if not is_valid_chord(t)]
    assert (
        not bad
    ), f"GRAMMAR.md documents these as valid but the parser rejects them: {bad}"


def test_every_banned_construct_fails_to_lint():
    # The banned snippets must each yield an error-severity finding from the pure parse+lint
    # pipeline (the iReal codec is out of scope for the standalone language core).
    snippets = [
        s.strip() for s in _block("banned-dsl", _grammar_text()).split("\n---\n")
    ]
    assert snippets, "no banned-dsl examples found"
    survivors = [s.splitlines()[0] for s in snippets if not _error_codes(s)]
    assert (
        not survivors
    ), f"GRAMMAR.md documents these as banned but they produced no error finding: {survivors}"
