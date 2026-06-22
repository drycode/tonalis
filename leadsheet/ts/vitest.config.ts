import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  test: {
    // Pure-language unit tests + the dsl-core conformance runner. The conformance tree is at the
    // repo root; `ts/` is now one level deeper under `leadsheet/`, so the runner is at
    // `../../conformance/...` (was `../conformance/...` before the leadsheet/ restructure).
    include: [
      "src/**/*.test.ts",
      "../../conformance/dsl-core/runners/ts/run.ts",
    ],
    // The conformance runner imports the library by its published package name; map it to the
    // local source so the in-repo suite resolves without a built/published artifact.
    alias: {
      tonalis: fileURLToPath(new URL("./src/index.ts", import.meta.url)),
    },
  },
});
