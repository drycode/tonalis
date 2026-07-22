# Contributing to Tonalis

Thanks for your interest. Tonalis is MIT-licensed and contributions are welcome.

## How to contribute

Tonalis uses the standard fork-and-PR flow — you do **not** need write access:

1. Fork the repo and create a branch off `main`.
2. Make your change (see the invariants below).
3. Run the checks locally, then open a pull request.

CI (`python`, `node`, `rust`, `fuzz`) must pass before a PR can be merged.
For a first-time contributor, a maintainer approves the workflow run before CI executes.

To report a bug or request a feature, [open an issue](https://github.com/drycode/tonalis/issues).

## The one rule that matters: keep the three ports in lockstep

Tonalis is one normative spec with three ports — a **Python reference**, plus
TypeScript and Rust — kept identical by a shared conformance corpus and a
differential fuzzer. Behavior is defined by the spec and the corpus, not by any
single port.

So, for any change to observable behavior:

1. **Land it in the Python reference first**, and add or update the conformance
   case(s) that pin the new behavior.
   Specs: [`conformance/tonalis/SPEC.md`](conformance/tonalis/SPEC.md) (lead-sheet)
   and [`conformance/music-dsl/SPEC-scales.md`](conformance/music-dsl/SPEC-scales.md).
2. **Port the same change to TypeScript and Rust** so all three pass the shared corpus.
3. **The fuzzer must stay at 0 divergences.**

A green PR that changes behavior in only one port will be sent back — that's
exactly the drift the conformance suite and fuzzer exist to catch.

## Running the checks locally

Per-port install and test commands live in the README under
**[Ports — install & test](README.md#ports--install--test)**; test-file
conventions are under **[Test conventions](README.md#test-conventions)**. The two
project-wide gates:

```bash
make fuzz                 # 3-way Python↔TS↔Rust differential fuzzer, 0 divergences required
mkdocs build --strict     # docs must build clean if you touched docs/
```

Run the conformance runners for each port (paths in the README) and confirm all
of `python` / `node` / `rust` / `fuzz` are green before you push — those are the
same jobs CI runs.

## Questions

Open an issue or start the conversation in your PR. We'd rather discuss a design
before you write three ports of it.
