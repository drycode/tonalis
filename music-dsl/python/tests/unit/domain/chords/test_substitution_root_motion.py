from music_dsl.domain.static import Notes
from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.numeric_chord import NumericChord


def test_substitution_fires_on_m6_root_motion_not_its_M3_inversion():
    # A = ascending semitones(chord.root -> key root), mod 12.
    # 'm6 up' and 'M3 down' BOTH give A=8 (the relationship branch 3 targets).
    # 'M3 up' gives A=4 -- the INVERSION; it must NOT trigger the m6 branch.

    # A=4: Ab up a M3 reaches C. Inversion of m6 -> substitution must NOT alter the degree.
    ab_plain = NumericChord._from_chord(Notes.C, Chord("Ab-7"), substitution=False)
    ab_sub = NumericChord._from_chord(Notes.C, Chord("Ab-7"), substitution=True)
    assert ab_sub.root.value == ab_plain.root.value, (ab_sub.root, ab_plain.root)

    # A=8: E up a m6 reaches C. Genuine m6 relationship -> substitution SHOULD alter it.
    e_plain = NumericChord._from_chord(Notes.C, Chord("E-7"), substitution=False)
    e_sub = NumericChord._from_chord(Notes.C, Chord("E-7"), substitution=True)
    assert e_sub.root.value != e_plain.root.value, (e_sub.root, e_plain.root)
