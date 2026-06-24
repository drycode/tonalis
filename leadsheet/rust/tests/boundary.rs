//! Import-boundary guard (Rust) — the dsl-core half of the §7 one-way-dependency invariant.
//!
//! In Rust the COMPILER is the guard: a forbidden `use SCRUBBED::...` in this crate simply would
//! not resolve (the crate has no such dependency), so the fact that `cargo test` builds + runs THIS
//! file standalone already proves tonalis does not depend on any adapter. This test makes the
//! invariant explicit and fails loudly with a clear message by asserting the crate's `Cargo.toml`
//! dependency table contains ONLY an allow-list of crates and NEVER an adapter crate
//! (`SCRUBBED`/`ireal-codec`/`text_target`/`text-target`).
//!
//! No TOML parser is pulled in (that would add a dependency to the pure core's dev surface and muddy
//! the point); a tiny line scanner over the `[dependencies]` section is sufficient and dependency-free.

use std::collections::BTreeSet;
use std::path::PathBuf;

/// Crate names the pure language core is allowed to depend on. (Forbidding everything else makes
/// the test an allow-LIST, so a future stray dep — adapter or otherwise — trips it.)
// music_dsl is the one-way leadsheet → theory-lib dependency (Phase 3). It is NOT an adapter
// (FORBIDDEN_DEPS), so adding it here keeps tonalis_has_no_adapter_dependency biting.
const ALLOWED_DEPS: &[&str] = &["regex", "serde", "serde_json", "music_dsl"];

/// Adapter crates that must NEVER appear (named explicitly for a crisp failure message).
const FORBIDDEN_DEPS: &[&str] = &["SCRUBBED", "ireal-codec", "text_target", "text-target"];

/// Parse dependency crate names out of every `[dependencies]` / `[dev-dependencies]` /
/// `[build-dependencies]` table in the Cargo.toml text. Returns the set of left-hand names.
fn dependency_names(cargo_toml: &str) -> BTreeSet<String> {
    let mut names = BTreeSet::new();
    let mut in_deps = false;
    for raw in cargo_toml.lines() {
        let line = raw.trim();
        if line.starts_with('[') {
            // a new table header — are we entering/leaving a *dependencies table?
            in_deps = line.contains("dependencies]");
            continue;
        }
        if !in_deps || line.is_empty() || line.starts_with('#') {
            continue;
        }
        // a dep line is `name = ...` (name may be quoted or bare; stop at '=' or whitespace).
        let name_part = line.split('=').next().unwrap_or("").trim().trim_matches('"');
        if !name_part.is_empty() {
            names.insert(name_part.to_string());
        }
    }
    names
}

fn read_cargo_toml() -> String {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("Cargo.toml");
    std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("cannot read {}: {e}", path.display()))
}

#[test]
fn tonalis_has_no_adapter_dependency() {
    let deps = dependency_names(&read_cargo_toml());
    for forbidden in FORBIDDEN_DEPS {
        assert!(
            !deps.contains(*forbidden),
            "tonalis Cargo.toml depends on adapter crate `{forbidden}` — the pure core must NOT \
             depend on SCRUBBED/text_target (one-way dep violated). deps = {deps:?}"
        );
    }
}

#[test]
fn tonalis_dependencies_are_within_the_allow_list() {
    let deps = dependency_names(&read_cargo_toml());
    let allowed: BTreeSet<&str> = ALLOWED_DEPS.iter().copied().collect();
    let unexpected: Vec<&String> = deps.iter().filter(|d| !allowed.contains(d.as_str())).collect();
    assert!(
        unexpected.is_empty(),
        "tonalis Cargo.toml has dependencies outside the allow-list {ALLOWED_DEPS:?}: {unexpected:?}"
    );
}

// NEGATIVE checks: the line-scanner classifier must BITE on a synthetic poisoned Cargo.toml (proves
// the guard is not a no-op). The real Cargo.toml is never modified.
#[test]
fn guard_bites_on_a_poisoned_cargo_toml() {
    let poisoned = "\
[package]
name = \"tonalis\"

[dependencies]
regex = \"1\"
SCRUBBED = { path = \"../../ireal-codec/rust\" }
";
    let deps = dependency_names(poisoned);
    assert!(
        deps.contains("SCRUBBED"),
        "the dependency scanner FAILED to see `SCRUBBED` in a poisoned Cargo.toml: {deps:?}"
    );
    // and the allow-list check would reject it
    let allowed: BTreeSet<&str> = ALLOWED_DEPS.iter().copied().collect();
    assert!(deps.iter().any(|d| !allowed.contains(d.as_str())));
}

#[test]
fn scanner_sees_a_clean_cargo_toml_as_clean() {
    let clean = "\
[dependencies]
regex = \"1\"
serde = { version = \"1\", features = [\"derive\"] }
serde_json = { version = \"1\" }
";
    let deps = dependency_names(clean);
    let allowed: BTreeSet<&str> = ALLOWED_DEPS.iter().copied().collect();
    assert!(deps.iter().all(|d| allowed.contains(d.as_str())), "clean deps misclassified: {deps:?}");
}
