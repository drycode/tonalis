"""Bounded, single-pass DSL parser. Never eval/exec; limit violations are findings.

DSL → ParseResult{LeadSheet, findings}. The parser records structure; the linter (lint.py)
judges chord validity, beat sums, etc. Header values are read literally to end-of-line.
"""

import re

from tonalis.ast import (
    Barline,
    Cell,
    LeadSheet,
    LintFinding,
    Measure,
    ParseResult,
    Section,
    SectionKind,
)

MAX_BYTES = 256 * 1024
MAX_LINES = 5000
MAX_LINE_LEN = 1000
MAX_MEASURES = 2000
MAX_CELLS_PER_MEASURE = 16
MAX_CHORD_TOKEN_LEN = 50
MAX_ALT_CHORD_TOKENS = 8
# Numeric value cap (SPEC.md §1.4): a meter num/den, a :N beat count, and an ending number must be
# <= MAX_METER. Exceeding it never reaches rendering, so no port can be driven into a multi-GB
# " "-padding allocation or a fixed-width-int overflow.
MAX_METER = 64

# Line terminators (SPEC.md §1.1): ONLY \r\n, \n, \r. NOT Python's broader str.splitlines() set
# (which also splits \v \f \x1c \x1d \x1e \x85    ) — those are ordinary characters here,
# so all ports split identically.
_LINE_SPLIT_RE = re.compile(r"\r\n|\r|\n")

_REQUIRED = ("title", "key", "time")
_META_KEYS = ("title", "composer", "style", "key", "time")
_SECTIONS = {
    "A": SectionKind.A,
    "B": SectionKind.B,
    "C": SectionKind.C,
    "D": SectionKind.D,
    "Intro": SectionKind.INTRO,
    "i": SectionKind.INTRO,
    "Verse": SectionKind.VERSE,
    "v": SectionKind.VERSE,
}
_BARLINE_RE = re.compile(r"(\{|\}|\|\||\||Z)")
_CELL_RE = re.compile(r"\([^)]*\)|\S+")  # a (alt) group, or a non-space run
_INLINE_ALT_RE = re.compile(r"^([^(]+)(\([^)]*\))$")  # "G7(Db7)" -> chord + (alt)
# ASCII digits only (SPEC.md §1.1): explicit [0-9] classes, never \d (Unicode-aware in Python).
_ENDING_RE = re.compile(r"^([0-9]+)\.\s*(.*)$")
_TIME_RE = re.compile(r"\[time:\s*([0-9]+)\s*/\s*([0-9]+)\s*\]\s*$")
_SECTION_RE = re.compile(r"\[([A-Za-z]+)([0-9]*)\]\s*$")


def _split_lines(text):
    """SPEC.md §1.1 line split: ONLY \\r\\n, \\n, \\r (not Python's wider splitlines() set).

    Mirrors ``str.splitlines()`` for these three forms — including dropping the trailing empty
    element a terminal newline would otherwise leave — so the common case is byte-identical, but
    a stray \\x1c/\\v/\\x85/etc. stays inside its line (an ordinary char), matching TS/Rust.
    """
    if text == "":
        return []
    parts = _LINE_SPLIT_RE.split(text)
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def _is_ascii_digits(s):
    """ASCII-only digit check (SPEC.md §1.1). Unlike ``str.isdigit()`` this rejects non-ASCII
    digits (``٣``) AND numeric-but-non-decimal characters (``²``, which would crash ``int()``).
    """
    return s != "" and all("0" <= c <= "9" for c in s)


def parse_dsl(text):
    findings = []

    def err(line, code, msg):
        findings.append(LintFinding("error", line, code, msg))

    def warn(line, code, msg):
        findings.append(LintFinding("warning", line, code, msg))

    if len(text.encode("utf-8", "replace")) > MAX_BYTES:
        err(0, "too-big", "input exceeds MAX_BYTES")
        return ParseResult(None, findings)
    text = text.lstrip("﻿")
    lines = _split_lines(text)
    if len(lines) > MAX_LINES:
        err(0, "too-big", "too many lines")
        return ParseResult(None, findings)
    for n, raw in enumerate(lines, 1):
        if len(raw) > MAX_LINE_LEN:
            err(n, "too-big", "line too long")
            return ParseResult(None, findings)

    meta = {}
    i, total = 0, len(lines)

    def assign_meta(k, v, lineno):
        # Header keys are singletons. Re-stating one is a duplicate (same value, redundant)
        # or a conflict (different value, mutually exclusive) — never silently last-wins.
        if k in meta:
            if meta[k] == v:
                warn(lineno, "duplicate-header", f"duplicate header {k!r}")
            else:
                err(
                    lineno,
                    "conflicting-header",
                    f"conflicting header {k!r}: {meta[k]!r} vs {v!r}",
                )
            return  # keep the first value; a conflict already blocks compile
        meta[k] = v

    # --- header ---
    while i < total:
        raw = lines[i]
        line = raw.strip()
        if line == "" or line.startswith("#"):
            i += 1
            continue
        if line[0] in "[|{":
            break
        m = re.match(r"([A-Za-z]+)\s*:\s*(.*)$", raw)  # value read literally to EOL
        if not m:
            break
        key, val = m.group(1).lower(), m.group(2).rstrip()
        if "=" in val:
            err(i + 1, "meta-delimiter", f"'=' not allowed in metadata value: {val!r}")
        if key == "time":
            # ASCII digits only (SPEC.md §1.1); both components must be <= MAX_METER (§1.4).
            tm = re.match(r"([0-9]+)\s*/\s*([0-9]+)$", val)
            if tm and int(tm.group(1)) <= MAX_METER and int(tm.group(2)) <= MAX_METER:
                assign_meta("time", (int(tm.group(1)), int(tm.group(2))), i + 1)
            else:
                err(i + 1, "bad-time", f"bad time signature: {val!r}")
        elif key in _META_KEYS:
            assign_meta(key, val, i + 1)
        else:
            warn(i + 1, "unknown-key", f"unknown header key: {key}")
        i += 1

    for k in _REQUIRED:
        if k not in meta:
            err(0, "missing-header", f"missing required header: {k}")
    if meta.get("title", "") == "":
        err(0, "missing-header", "title must be non-empty")

    # --- body ---
    sections = []
    cur = None
    pending_nav = []
    pending_hints = []
    measure_count = 0
    current_time = meta.get("time", (4, 4))  # for redundant mid-chart [time:] detection

    def ensure_section():
        nonlocal cur
        if cur is None:
            cur = Section(label="A", kind=SectionKind.A)
            sections.append(cur)
        return cur

    while i < total:
        raw = lines[i]
        line = raw.strip()
        ln = i + 1
        i += 1
        if line == "" or line.startswith("#"):
            continue
        tm = _TIME_RE.match(line)
        if line.startswith("[time") and tm:
            n, d = int(tm.group(1)), int(tm.group(2))
            if n > MAX_METER or d > MAX_METER:
                # recognized [time:…] shape but the meter is out of range (SPEC.md §1.4/§4.4):
                # reject it as bad-time; it contributes no nav.
                err(ln, "bad-time", f"meter component exceeds MAX_METER: {n}/{d}")
                continue
            newt = (n, d)
            if newt == current_time:
                warn(
                    ln,
                    "redundant-time",
                    f"[time: {newt[0]}/{newt[1]}] repeats the current meter",
                )
            current_time = newt
            pending_nav.append(("time", newt))
            continue
        sec = _SECTION_RE.match(line)
        if sec:
            name = sec.group(1)
            kind = _SECTIONS.get(name)
            if kind is None:
                err(
                    ln,
                    "unknown-section",
                    f"unknown section {name!r}; allowed: A-D, Intro, Verse",
                )
                kind = SectionKind.A
            cur = Section(label=name + sec.group(2), kind=kind)
            sections.append(cur)
            continue
        if line.startswith("@"):
            if "segno" in line:
                pending_nav.append(("segno",))
            elif "tocoda" in line or "to coda" in line or "to-coda" in line:
                # "To Coda" jump-point: a Q AFTER the PRECEDING measure's chords (not the
                # next one). Checked before "coda" because "tocoda" contains "coda".
                if cur is not None and cur.measures:
                    cur.measures[-1].nav = cur.measures[-1].nav + (("tocoda",),)
                else:
                    warn(
                        ln, "tocoda-without-measure", "@tocoda has no preceding measure"
                    )
            elif "fine" in line:
                pending_nav.append(("fine",))
            elif "coda" in line:
                pending_nav.append(("coda",))
            elif "break" in line or "newline" in line:
                # page-layout only — NO lead-sheet semantics. Demoted to an opaque
                # render-hint (Phase 2 §3.3); a downstream codec reads it, text-target ignores it.
                pending_hints.append("break")
            else:
                warn(ln, "unknown-nav", f"unknown @directive: {line}")
            continue
        if line.startswith("<") and line.endswith(">"):
            pending_nav.append(("text", line))
            continue
        # otherwise: a measure line
        section = ensure_section()
        measures = _parse_measure_line(line, ln, err, warn)
        for m in measures:
            if pending_nav:
                m.nav = tuple(pending_nav) + m.nav
                pending_nav = []
            if pending_hints:
                m.hints = tuple(pending_hints) + m.hints
                pending_hints = []
            section.measures.append(m)
            measure_count += 1
            if measure_count > MAX_MEASURES:
                err(ln, "too-big", "too many measures")
                return ParseResult(LeadSheet(meta=meta, sections=sections), findings)

    if not sections or all(not s.measures for s in sections):
        err(0, "empty-chart", "no sections or measures")
    return ParseResult(LeadSheet(meta=meta, sections=sections), findings)


def _parse_measure_line(line, ln, err, warn):
    parts = _BARLINE_RE.split(line)
    measures = []
    bar_open = False
    buf = None
    for p in parts:
        if p == "{":
            bar_open = True
            continue
        if p in ("|", "}", "||", "Z"):
            if buf is not None and buf.strip() != "":
                if p in ("||", "Z"):
                    close = Barline.FINAL
                elif p == "}":
                    close = Barline.REPEAT_END
                else:
                    close = Barline.NORMAL
                ending, cells = _parse_cells(buf, ln, err, warn)
                measures.append(
                    Measure(
                        cells=cells,
                        ending=ending,
                        bar_open=bar_open,
                        barline=close,
                        line=ln,
                    )
                )
                bar_open = False
            elif p == "}" and measures:
                measures[-1].barline = Barline.REPEAT_END
            buf = None
            continue
        if p.strip() != "":
            buf = p
    if buf is not None and buf.strip() != "":
        ending, cells = _parse_cells(buf, ln, err, warn)
        measures.append(
            Measure(
                cells=cells, ending=ending, bar_open=bar_open, barline=Barline.NORMAL, line=ln
            )
        )
    return measures


def _parse_cells(content, ln, err, warn):
    content = content.strip()
    ending = None
    m = _ENDING_RE.match(content)
    if m:
        ending = int(m.group(1))
        content = m.group(2).strip()
        # An ending number > MAX_METER (SPEC.md §1.4) is a typo and would otherwise overflow a
        # fixed-width int in the ports; reject with the generic size-cap code.
        if ending > MAX_METER:
            err(ln, "too-big", f"ending number exceeds MAX_METER: {ending}")
    cells = []
    for tok in _CELL_RE.findall(content):
        if tok.startswith("("):
            if len(tok.strip("()").split()) > MAX_ALT_CHORD_TOKENS:
                err(ln, "alt-too-long", "alt chord has too many tokens")
            if cells:
                cells[-1].alt = tok
            else:
                warn(ln, "alt-without-chord", f"alt group {tok} has no preceding chord")
            continue
        # Split an inline alt off the chord, e.g. "G7(Db7)" -> chord "G7" + alt "(Db7)"
        # (lead-sheet notation writes alts with no space; the space-separated "G7 (Db7)" form is handled
        # by the `tok.startswith("(")` branch above).
        inline_alt = None
        am = _INLINE_ALT_RE.match(tok)
        if am:
            tok, inline_alt = am.group(1), am.group(2)
            if len(inline_alt.strip("()").split()) > MAX_ALT_CHORD_TOKENS:
                err(ln, "alt-too-long", "alt chord has too many tokens")
        chord, beats = tok, None
        if ":" in tok:
            chord, _, b = tok.partition(":")
            # ASCII digits only (SPEC.md §1.1) — str.isdigit() accepts non-ASCII digits and
            # numeric-but-non-decimal chars like '²' (which would crash int()). Cap at MAX_METER.
            if _is_ascii_digits(b):
                if int(b) > MAX_METER:
                    err(ln, "bad-beats", f"beat count exceeds MAX_METER in {tok!r}")
                else:
                    beats = int(b)
            else:
                err(ln, "bad-beats", f"bad beat count in {tok!r} (expected :<digits>)")
        if len(chord) > MAX_CHORD_TOKEN_LEN:
            err(ln, "token-too-long", f"chord token too long: {chord[:20]}…")
        cells.append(Cell(chord=chord, beats=beats, alt=inline_alt))
        if len(cells) > MAX_CELLS_PER_MEASURE:
            err(ln, "too-big", "too many cells in a measure")
            break
    return ending, cells
