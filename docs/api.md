# API reference

The per-language API references are **generated** from the source of each port by
`docs/build_api.sh` — never hand-written — so they stay in lockstep with the code.

Run the generators from the repository root:

```bash
bash docs/build_api.sh
```

This writes static HTML into `docs/api/**` (git-ignored), which the mkdocs site
then serves and the GitHub Pages workflow rebuilds on every deploy:

| Port | Generator | Output directory | Served path on the built site |
|------|-----------|------------------|-------------------------------|
| Python (`music_dsl` + `tonalis`) | [`pdoc`](https://pdoc.dev) | `docs/api/python/` | `api/python/` |
| TypeScript (`music-dsl/ts` + `tonalis/ts`) | [`typedoc`](https://typedoc.org) | `docs/api/ts/` | `api/ts/` |
| Rust (`music-dsl/rust` + `tonalis/rust`) | `cargo doc --no-deps` | `docs/api/rust/` | `api/rust/` |

!!! note "Generated locally / in CI, not committed"
    The `docs/api/**` trees are git-ignored and are **not** present in a bare
    checkout. They are produced by `build_api.sh` and served from the **built**
    site — locally after you run the generators, and on the published GitHub
    Pages site (the deploy workflow runs `build_api.sh` before `mkdocs build`).
    Because they are absent from a plain `mkdocs build`, this hub page links the
    generator tools rather than the (possibly-missing) generated pages; on the
    built site each port lives at the served path in the table above.

    Each generator is best-effort: if a language toolchain (pdoc / typedoc /
    cargo) is missing, `build_api.sh` skips that port and writes a placeholder
    page so the site still builds.

## Deployment

The GitHub Pages workflow (`.github/workflows/docs.yml`) runs `build_api.sh` and
then `mkdocs build` before deploying, so the published site always carries fresh
API references. The deploy step is gated and only serves once the repository is
made public — see the workflow and the README for details.
