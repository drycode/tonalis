/**
 * Vitest config for the Python↔TS differential fuzzer.
 * Run from music-dsl/ts/ with an explicit config path:
 *   cd music-dsl/ts
 *   node node_modules/.bin/vitest run --config ../../conformance/music-dsl/fuzz/vitest.fuzz.config.ts
 *
 * Uses the music-dsl/ts node_modules for vitest (the fuzz dir has no node_modules).
 */
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore — vitest/config resolves from music-dsl/ts/node_modules at runtime
import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      "@tonalis/music-dsl": join(HERE, "../../../music-dsl/ts/src/index.ts"),
    },
  },
  test: {
    include: [join(HERE, "ts_diff.test.ts")],
    alias: {
      "@tonalis/music-dsl": join(HERE, "../../../music-dsl/ts/src/index.ts"),
    },
  },
});
