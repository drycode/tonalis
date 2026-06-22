"""DSL linter: structural + chord-grammar checks over a parsed LeadSheet.

Errors block compilation; warnings don't. Uses the real chord grammar (chord_grammar) for
bad-chord, not the permissive CST scanner.
"""

from tonalis.ast import Barline, LintFinding
from tonalis.chord_grammar import is_valid_chord

# corpus-derived known-good uneven :N layouts (4/4); all-equal splits are always fine.
_ALLOWED_UNEVEN = {(2, 1, 1), (1, 1, 1, 1), (1, 1, 2), (3, 1), (1, 3), (2, 2)}


def _all_measures(chart):
    return [(s, m) for s in chart.sections for m in s.measures]


def _beat_pattern(measure, numerator):
    """Per-cell beat counts: explicit :N consume their count; unannotated split the
    remainder evenly. Returns (pattern_tuple, ok) where ok is False if it can't fill the bar.
    """
    cells = measure.cells
    if not cells:
        return (), True
    explicit = sum(c.beats for c in cells if c.beats)
    unannotated = [c for c in cells if not c.beats]
    remainder = numerator - explicit
    if unannotated:
        if remainder <= 0 or remainder % len(unannotated) != 0:
            return tuple(c.beats or 0 for c in cells), False
        each = remainder // len(unannotated)
        return tuple(c.beats if c.beats else each for c in cells), True
    return tuple(c.beats for c in cells), explicit == numerator


def lint(chart):
    findings = []

    def err(line, code, msg):
        findings.append(LintFinding("error", line, code, msg))

    def warn(line, code, msg):
        findings.append(LintFinding("warning", line, code, msg))

    measures = _all_measures(chart)
    numerator = (chart.meta.get("time") or (4, 4))[0]

    # repeats / endings balance, codas/segno, final bar, per-measure beats + chords
    balance = n_coda = n_segno = 0
    last_idx = len(measures) - 1
    for idx, (section, m) in enumerate(measures):
        for nav in m.nav:
            if nav == ("coda",):
                n_coda += 1
            elif nav == ("segno",):
                n_segno += 1
            elif nav and nav[0] == "time":
                numerator = nav[1][0]
        if m.bar_open:
            balance += 1
        if m.barline == Barline.REPEAT_END:
            if balance == 0:
                err(m.line, "unbalanced-repeat", "'}' with no matching '{'")
            else:
                balance -= 1
        if m.barline == Barline.FINAL and idx != last_idx:
            warn(
                m.line,
                "mid-final-bar",
                "final barline (Z/||) is not on the last measure",
            )

        # chords
        for c in m.cells:
            if c.chord and not is_valid_chord(c.chord):
                err(m.line, "bad-chord", f"invalid chord token: {c.chord!r}")
            if c.alt:
                for tok in c.alt.strip("()").split():
                    if not is_valid_chord(tok):
                        err(m.line, "bad-chord", f"invalid alt chord: {tok!r}")

        # empty measure
        if not m.cells:
            warn(m.line, "empty-measure", "measure has no chords (emitted as N.C.)")
            continue

        # beats. Pickup relaxation only excuses an UNDER-full first/last bar (anacrusis);
        # an OVER-full bar is always wrong, even for a pickup.
        pattern, ok = _beat_pattern(m, numerator)
        total = sum(pattern)
        is_pickup = idx in (0, last_idx)
        if total > numerator:
            err(m.line, "beat-sum", f"beats {pattern} overflow a {numerator}-beat bar")
        elif not ok and not is_pickup:
            err(
                m.line,
                "beat-sum",
                f"beats {pattern} do not fill a {numerator}-beat bar",
            )
        elif ok and len(set(pattern)) > 1 and pattern not in _ALLOWED_UNEVEN:
            warn(
                m.line,
                "beat-unsupported",
                f"uneven beat layout {pattern} not in the allowlist; even-split fallback",
            )

    if balance != 0:
        err(0, "unbalanced-repeat", f"{balance} unclosed '{{'")
    # an empty section (header but no measures) silently drops in render — surface it
    for section in chart.sections:
        if not section.measures:
            warn(
                0,
                "empty-section",
                f"section [{section.label}] has no measures (dropped)",
            )
    # nth endings must belong to a repeat (a section with endings needs a bar_open)
    for section in chart.sections:
        has_open = any(m.bar_open for m in section.measures)
        if any(m.ending for m in section.measures) and not has_open:
            ln = next((m.line for m in section.measures if m.ending), 0)
            err(ln, "ending-without-repeat", "nth ending outside a repeat block")
    if n_coda > 2:
        err(
            0,
            "coda-count",
            f"{n_coda} coda points (max 2 — the encoder cannot flatten more)",
        )
    elif n_coda == 2 and n_segno == 0:
        warn(
            0,
            "coda-needs-segno",
            "2-coda jump without @segno (will play D.C., not D.S.)",
        )

    return findings
