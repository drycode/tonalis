# Release on merge — committer-declared version, CI-verified

## Context

Tonalis publishes six artifacts from one version: the theory library
(`tonalis-music-dsl` on PyPI/crates.io, `@tonalis/music-dsl` on npm) and the DSL
(`tonalis` on all three). Until now `release.yml` fired on a pushed `v*` tag and
a human bumped sixteen version locations by hand, tagged, and hoped. The 0.1.1
release exposed three defects in that model:

1. **Nothing forced a release.** A merge published nothing; the tag was a
   separate manual act that could be skipped or forgotten.
2. **A partial release could not be repaired.** When PyPI/npm Trusted Publishers
   were missing, three of six jobs failed. Rerunning them re-attempted every
   artifact, including the already-published crates, which fail on duplicate
   versions. Recovery was manual `cargo publish` from a laptop — exactly the
   stored-credential path OIDC exists to eliminate.
3. **A hardcoded pin drifted.** `release.yml` rewrote the npm dependency range
   to a literal `^0.1.1`, so the next release would have shipped `tonalis`
   depending on a stale theory library.

## Requirements

- Every pull request merged to `main` produces a semantic release.
- The committer declares the version; CI verifies it and refuses anything else.
- `release.yml` is the only workflow that publishes. No laptop publishing.
- A partially failed release is repairable by rerunning it.

## Approach

**The committer owns the version. CI is the referee.** A pull request that does
not carry a legal version increment cannot merge; a merge that does publishes
automatically.

Rejected alternatives:

- **`semantic-release` over Conventional Commits** — requires replacing the
  established `[topic] Summary` title convention and infers intent from prose.
- **Release Please** — interposes a second release pull request, so a merge does
  not release; it queues a request to release.
- **CI-authored version-bump commit** — needs a bot identity with write access
  to `main` and turns every merge into two commits.

### The version surface

Sixteen authored locations carry the version. `scripts/release_surface.py` is
their single registry, and every other script and workflow reads it:

| group | count | locations |
| -- | -- | -- |
| package manifests | 6 | `{tonalis,music-dsl}/{python/pyproject.toml,rust/Cargo.toml,ts/package.json}` |
| internal pins | 2 | `tonalis/python` → `tonalis-music-dsl==X.Y.Z`; `tonalis/rust` → `music_dsl` dependency `version` |
| lockfiles | 8 | both `Cargo.lock` packages, both `package-lock.json` roots, and the `tonalis/ts` linked-dependency entry |

`scripts/set_version.py X.Y.Z` rewrites all sixteen deterministically, so the
committer runs one command rather than editing four file formats by hand.

### Pull request gate — `version-gate.yml`

Required check on every pull request into `main`. It fails unless:

1. All sixteen locations agree with each other.
2. The version is a **single legal SemVer step** from the base branch: exactly
   one of `PATCH+1`, `MINOR+1` with patch reset, or `MAJOR+1` with both reset.
   A skip (`0.1.1` → `0.1.5`), a downgrade, an unchanged version, or a
   pre-release suffix all fail. There is no "no release" escape: every merge
   ships, so every pull request bumps.
3. The declared version is absent from all six registries — versions are
   immutable, so a collision must fail before merge, not mid-publish.
4. The version currently on `main` is present in all six registries. This
   refuses to stack a new release on top of a half-published one, which is the
   failure the 0.1.1 release actually hit.

Check 4 could deadlock a pull request whose purpose is to repair a broken
release, so it — and only it — is skipped when the pull request carries the
`release:override` label. Failing closed with one auditable escape beats failing
open.

### Release — `release.yml`

Trigger changes from `push: tags: v*` to `push: branches: [main]`. The tag stops
being the trigger and becomes the record.

- `ci` — the full Python/TypeScript/Rust suite, conformance runners, and the
  three-way differential fuzzer, reused verbatim via `workflow_call`.
- `guard` — re-verifies the sixteen locations agree, then queries the six
  registries and emits one boolean per artifact.
- Six publish jobs, each `if:` its own guard flag. An artifact already present
  at this version is skipped, not retried, so **rerunning a partially failed
  release completes it** and a merge that carries no bump is a clean no-op
  instead of six duplicate-version failures. Dependent jobs tolerate a skipped
  base library via `!cancelled()` plus an explicit non-failure check, since a
  skipped `needs` would otherwise cascade. `!cancelled()` also drops the implicit
  success requirement on `needs`, so those jobs re-assert `ci` and `guard`
  explicitly rather than inheriting a gate they no longer have.
- The npm dependency range is derived from the manifest at publish time, killing
  the hardcoded `^0.1.1`.
- `record` — asks the registries whether all six artifacts are live, then creates
  tag `vX.Y.Z` and a GitHub Release with generated notes, both idempotently.
  Interrogating the registries is deliberate: a skipped dependent job is
  indistinguishable from a successful one by job result alone, so only the
  registries can prove the release landed. A missing artifact fails this job and
  writes no tag. `GITHUB_TOKEN`-created tags do not trigger workflows, and
  `release.yml` no longer listens for tags, so there is no recursion.

`release.yml` uses the `tonalis-release` concurrency group with cancellation
disabled, so two merges cannot publish concurrently and a queued release is never
discarded. The gate uses a per-pull-request group instead — serialising it behind
releases would let GitHub cancel a queued gate run.

`ci.yml` loses its `push: branches: [main]` trigger. `release.yml` now runs that
exact suite on every merge, so keeping the trigger would run it twice.

## Testing

`scripts/tests/test_release_scripts.py` covers the logic that has no other
guard, and runs in the `ci` Python job:

- Every SemVer step is classified, and skips, downgrades, equality, and
  pre-release suffixes are rejected.
- `set_version.py` rewrites all sixteen locations and leaves the tree agreeing
  with itself.
- Rewriting the current version is byte-identical, proving the JSON and TOML
  writers preserve formatting rather than reflowing generated lockfiles.
- Registry URL construction, including the npm scoped-name escape, and the
  200/404 presence mapping. An unexpected status raises instead of guessing
  "absent" — guessing would publish over a real release.

End-to-end proof is this change itself: it bumps to `0.1.2`, so merging it
exercises the gate and the new release path against live registries.

## Consequences

- Every merge consumes a version number. Documentation-only changes ship a patch
  release. This is the accepted cost of "every merge releases".
- A rapid double merge can have GitHub cancel the queued intermediate release.
  Recovery is rerunning that run, which the idempotent publish jobs make safe.
- crates.io Trusted Publishing must be configured for both crates before the
  next release, since manual publishing is now closed off.
