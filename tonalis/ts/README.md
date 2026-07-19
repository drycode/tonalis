# tonalis

A generic, format-agnostic music-harmony DSL for lead sheets: parse chord
charts to a canonical AST, lint them with structured findings, and render back
to canonical text or JSON. Ships compiled ESM with type declarations. The
TypeScript port conforms to the same normative spec as the Python reference
and the Rust port via a shared 255-case conformance suite.

Music-theory questions (chord validity, scales, keys) are delegated to the
pure [`@tonalis/music-dsl`](https://www.npmjs.com/package/@tonalis/music-dsl)
theory library — the package's only runtime dependency.

## Install

```bash
npm install tonalis
```

## Use

```ts
import { parseDsl, lint, serialize, astToJson } from "tonalis";

const result = parseDsl(text);
const findings = [...result.findings, ...(result.chart ? lint(result.chart) : [])];
const json = result.chart ? astToJson(result.chart) : null;
const canonical = result.chart ? serialize(result.chart) : null;
```

## Links

- Source, spec, docs, and conformance suite: <https://github.com/drycode/tonalis>
- License: MIT
