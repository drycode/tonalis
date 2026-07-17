from music_dsl.domain.static import ScaleDegree
from music_dsl.domain.static.scale_degree import _SHARPS_TO_FLATS


def _enharmonic_degree_pairs():
    return [(ScaleDegree(sharp_val), ScaleDegree(flat_val)) for sharp_val, flat_val in _SHARPS_TO_FLATS.items()]


def test_enharmonic_scale_degrees_hash_equal():
    pairs = _enharmonic_degree_pairs()
    assert pairs, "expected at least one enharmonic ScaleDegree pair"
    for s, f in pairs:
        assert s == f, (s, f)            # enharmonic-degree equality (already correct)
        assert hash(s) == hash(f), (s, f)  # the consistency fix under test
