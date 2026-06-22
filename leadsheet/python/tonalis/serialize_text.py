"""Deterministic canonical-DSL pretty-printer: LeadSheet -> DSL text (Phase 2 §1.1).

The inverse direction of ``parser.parse_dsl`` for the canonical form. ``parse(serialize(ir)) == ir``
is gated by the conformance suite; this printer is the only place IR -> text lives.
"""

from tonalis.ast import Barline, LeadSheet, Measure, Section

_HEADER_ORDER = ("title", "composer", "style", "key", "time")
_BARLINE_GLYPH = {
    Barline.NORMAL: "|",
    Barline.REPEAT_END: "}",
    Barline.FINAL: "||",
}


def _header(meta: dict) -> str:
    out = []
    for k in _HEADER_ORDER:
        if k not in meta:
            continue
        v = meta[k]
        if k == "time":
            out.append(f"time: {v[0]}/{v[1]}")
        else:
            out.append(f"{k}: {v}")
    return "\n".join(out)


def _cell_str(cell) -> str:
    s = cell.chord
    if cell.beats is not None:
        s += f":{cell.beats}"
    if cell.alt:
        # A single-token alt glues inline (`G7(Db7)`, the grammar's "inline alt, no space" form),
        # but a MULTI-token alt carries an interior space (`(A-7 D7)`) and the glued form
        # `G7(A-7 D7)` re-tokenizes wrong (the cell scanner `\([^)]*\)|\S+` breaks at the space).
        # Emit the separated `chord (alt)` form so `parse(serialize(ir)) == ir` holds (SPEC §2.1).
        s += (" " if " " in cell.alt else "") + cell.alt
    return s


def _nav_lines_before(m: Measure) -> list:
    lines = []
    for item in m.nav:
        head = item[0]
        if head == "segno":
            lines.append("@segno")
        elif head == "coda":
            lines.append("@coda")
        elif head == "fine":
            lines.append("@fine")
        elif head == "text":
            lines.append(item[1])
        elif head == "time":
            lines.append(f"[time: {item[1][0]}/{item[1][1]}]")
        # tocoda is emitted AFTER the measure (see _nav_after)
    return lines


def _nav_after(m: Measure) -> list:
    return ["@tocoda" for item in m.nav if item and item[0] == "tocoda"]


def _measure_str(m: Measure, *, first_on_line: bool) -> str:
    # Canonical body line: a leading "| " opens the line, measures are "| "-joined, and each
    # measure ends with its barline glyph. A repeat-open prefixes "{ ".
    prefix = "{ " if m.bar_open else ("| " if first_on_line else "")
    body = ""
    if m.ending is not None:
        body += f"{m.ending}. "
    body += " ".join(_cell_str(c) for c in m.cells)
    return f"{prefix}{body} {_BARLINE_GLYPH[m.barline]}"


def _section_text(s: Section) -> str:
    # One body line per section (parser-faithful): directives (@break/@segno/.../<text>) sit on
    # their own line and FLUSH the in-progress measure line before them; @tocoda flushes after.
    lines = [f"[{s.label}]"]
    run = []  # measures accumulating on the current body line

    def flush():
        if run:
            lines.append(" ".join(run))
            run.clear()

    for m in s.measures:
        before = []
        for h in m.hints:
            if h == "break":
                before.append("@break")
        before.extend(_nav_lines_before(m))
        if before:
            flush()
            lines.extend(before)
        run.append(_measure_str(m, first_on_line=not run))
        after = _nav_after(m)
        if after:
            flush()
            lines.extend(after)
    flush()
    return "\n".join(lines)


def serialize(chart: LeadSheet) -> str:
    """Canonical DSL text for a LeadSheet (trailing newline; section blocks blank-line separated)."""
    parts = [_header(chart.meta)]
    for s in chart.sections:
        parts.append("")  # blank line before each section
        parts.append(_section_text(s))
    return "\n".join(parts) + "\n"
