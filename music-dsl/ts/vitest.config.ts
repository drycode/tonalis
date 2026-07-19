import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  test: {
    include: [
      "src/**/*.test.ts",
      "../../conformance/music-dsl/runners/ts/run.ts",
    ],
    alias: {
      "@tonalis/music-dsl": fileURLToPath(new URL("./src/index.ts", import.meta.url)),
    },
  },
});
