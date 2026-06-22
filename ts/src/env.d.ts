/**
 * Minimal ambient declarations for the one runtime global the core touches: `TextEncoder`.
 *
 * `TextEncoder` is a WHATWG Encoding API global present in every modern browser and in Node
 * (>=11). We declare just the surface we use so the core typechecks WITHOUT pulling in the full
 * `lib.dom.d.ts` (which would imply a DOM environment) or `@types/node` (which would imply Node).
 * The runtime code also guards `typeof TextEncoder !== "undefined"` and falls back to a hand-
 * rolled UTF-8 encoder, so the package stays correct even where the global is absent.
 */

interface TextEncoder {
  encode(input?: string): Uint8Array;
}

interface TextEncoderConstructor {
  new (): TextEncoder;
}

declare const TextEncoder: TextEncoderConstructor | undefined;
