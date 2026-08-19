# Releasing

**Every pull request merged to `main` publishes a release.** There is no separate
release step, no release branch, and no manual publishing. The committer declares
the version; CI verifies it and does the publishing.

Six artifacts ship from one version:

| | PyPI | npm | crates.io |
| -- | -- | -- | -- |
| theory library | `tonalis-music-dsl` | `@tonalis/music-dsl` | `tonalis-music-dsl` |
| lead-sheet DSL | `tonalis` | `tonalis` | `tonalis` |

## Making a change

Bump the version as part of your pull request:

```bash
python scripts/set_version.py --bump patch   # or minor, or major
```

That rewrites all sixteen authored locations — six package manifests, the two
internal pins, and eight lockfile entries — so nothing is left behind. Commit the
result with the rest of your change.

Choose the bump by what the change does to the public surface of any port:

- **patch** — a fix or an internal change; no surface change.
- **minor** — new surface, existing surface unchanged.
- **major** — existing surface changed or removed.

Because every merge ships, there is no "no release" option. A documentation-only
change ships a patch release.

## What CI enforces

`version-gate.yml` runs on every pull request and fails unless:

1. All sixteen locations agree on one version.
2. The version is exactly one SemVer step from `main` — `PATCH+1`, `MINOR+1` with
   patch reset, or `MAJOR+1` with both reset. A skip like `0.1.1` → `0.1.5` is a
   typo, not an intent.
3. No registry has already published that version. Versions are immutable.
4. The version currently on `main` is published in all six registries, so a new
   release never stacks on a half-published one.

## What happens on merge

`release.yml` runs on the push to `main`:

1. `ci` — the full Python/TypeScript/Rust suite, conformance runners, and the
   three-way differential fuzzer.
2. `guard` — re-checks the version surface and asks each registry what already
   exists.
3. Six publish jobs, each skipped if that artifact is already published, using
   OIDC trusted publishing. The theory library goes first; the DSL follows.
4. `record` — confirms all six artifacts are live, then creates tag `vX.Y.Z` and a
   GitHub Release with generated notes.

## When a release partially fails

Publishing is idempotent, so **rerun the failed release run**. Each publish job
skips whatever already landed and retries only what is missing. Do this before
merging another pull request — the gate will otherwise block the next one, which
is the point.

If the repair itself needs a code change, label that pull request
`release:override` to bypass the "previous release is complete" check.

## Registry prerequisites

Each registry needs a one-time Trusted Publisher, configured in its own UI, for
both packages:

```text
Owner / organization:  drycode
Repository:            tonalis
Workflow:              release.yml
Environment:           (leave blank)
```

- PyPI — <https://pypi.org/manage/project/tonalis-music-dsl/settings/publishing/>
  and the same page for `tonalis`.
- npm — package settings → Trusted Publisher.
- crates.io — `https://crates.io/crates/<crate>/settings` → Trusted Publishing.

Without a publisher, that one job fails and the rest are unaffected; add the
publisher and rerun the run.

## Design

`docs/specs/2026-08-19-release-on-merge-design.md`.
