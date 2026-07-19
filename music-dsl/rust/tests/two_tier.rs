//! Focused two-tier scale-model unit (DRY-432). The refusal contract was
//! previously exercised in Rust only via conformance, so a regression would
//! not localize. Tier 1: membership (`contains`) answers on every scale.
//! Tier 2: functional queries (`is_diatonic`) refuse with
//! `TransactionError::NonFunctionalScale` on scales without a tonal hierarchy.

use music_dsl::encode::{contains, SCALES};
use music_dsl::transactions::{is_diatonic, TransactionError};

fn descriptor(name: &str) -> &'static music_dsl::encode::ScaleDescriptor {
    &SCALES.iter().find(|(n, _)| *n == name).unwrap().1
}

#[test]
fn functional_scale_answers_is_diatonic() {
    assert!(is_diatonic("C", descriptor("Major"), "C^7").unwrap());
    assert!(!is_diatonic("C", descriptor("Major"), "C#^7").unwrap());
}

#[test]
fn every_non_functional_scale_refuses_is_diatonic() {
    let mut checked = 0;
    for (name, desc) in SCALES {
        if desc.supports_diatonic_function {
            continue;
        }
        match is_diatonic("C", desc, "C7") {
            Err(TransactionError::NonFunctionalScale(_)) => checked += 1,
            other => panic!("{name} must refuse functional queries, got {other:?}"),
        }
    }
    assert!(checked > 0, "expected at least one non-functional scale");
}

#[test]
fn contains_answers_on_non_functional_scales() {
    let chromatic = descriptor("Chromatic");
    for pc in 0..12 {
        assert!(contains(chromatic, pc), "Chromatic must contain pc {pc}");
    }
    let whole_tone = descriptor("WholeTone");
    assert!(contains(whole_tone, 0));
    assert!(!contains(whole_tone, 1));
}
