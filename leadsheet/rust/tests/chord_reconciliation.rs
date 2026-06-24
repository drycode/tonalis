//! Frozen reconciliation: the music_dsl-backed validator must agree with the shared oracle
//! (leadsheet/fixtures/chord_oracle.json) for every corpus token, except the blessed {C7777}.
//! Same ground truth the Python + TS ports assert against.

use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

use tonalis::is_valid_chord;

fn oracle() -> HashMap<String, bool> {
    // From leadsheet/rust/ (CARGO_MANIFEST_DIR) → ../fixtures/ = leadsheet/fixtures/.
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../fixtures/chord_oracle.json");
    let raw = fs::read_to_string(&path).expect("read shared chord_oracle.json");
    serde_json::from_str(&raw).expect("parse chord_oracle.json")
}

const BLESSED: &[&str] = &["C7777"]; // old regex wrongly accepted; music_dsl correctly rejects.

#[test]
fn new_validator_matches_frozen_oracle() {
    let o = oracle();
    let mismatches: Vec<&String> = o
        .iter()
        .filter(|(t, &old)| is_valid_chord(t) != old && !BLESSED.contains(&t.as_str()))
        .map(|(t, _)| t)
        .collect();
    assert!(
        mismatches.is_empty(),
        "{} drift from oracle: {:?}",
        mismatches.len(),
        &mismatches[..mismatches.len().min(20)]
    );
}

#[test]
fn blessed_differences_are_live() {
    let o = oracle();
    for t in BLESSED {
        assert_eq!(o.get(*t), Some(&true), "{t}: not old=true in oracle (stale bless)");
        assert!(!is_valid_chord(t), "{t}: not new=false (stale bless)");
    }
}
