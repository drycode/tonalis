from music_dsl.domain.static import Notes


def test_enharmonic_notes_are_equal():
    assert Notes.Cs == Notes.Db
    assert Notes.Ds == Notes.Eb
    assert Notes.C != Notes.D


def test_enharmonic_notes_hash_equal():
    # the contract: a == b  =>  hash(a) == hash(b)
    for sharp, flat in [(Notes.Cs, Notes.Db), (Notes.Ds, Notes.Eb),
                        (Notes.Fs, Notes.Gb), (Notes.Gs, Notes.Ab), (Notes.As, Notes.Bb)]:
        assert sharp == flat, (sharp, flat)          # enharmonic equality (already correct)
        assert hash(sharp) == hash(flat), (sharp, flat)  # the consistency fix under test


def test_enharmonic_notes_dedup_in_a_set():
    # the observable consequence of consistent eq/hash
    assert len({Notes.Cs, Notes.Db}) == 1
