/**
 * Focused two-tier scale-model unit (DRY-432). The refusal contract was
 * previously exercised in TS only via conformance, so a regression would not
 * localize. Tier 1: membership (`contains`) answers on every scale. Tier 2:
 * functional queries (`isDiatonic`) refuse with NonFunctionalScaleError on
 * scales without a tonal hierarchy instead of fabricating an answer.
 */
import { describe, expect, it } from "vitest";
import { Scales, NonFunctionalScaleError, contains } from "./encode.js";
import { isDiatonic } from "./transactions.js";
import { parseChord } from "./chord.js";

describe("two-tier scale model", () => {
  it("functional scales answer isDiatonic", () => {
    expect(isDiatonic("C", "Major", parseChord("C^7"))).toBe(true);
    expect(isDiatonic("C", "Major", parseChord("C#^7"))).toBe(false);
  });

  it("non-functional scales refuse isDiatonic with NonFunctionalScaleError", () => {
    for (const name of Object.keys(Scales)) {
      const descriptor = Scales[name]!;
      if (descriptor.supportsDiatonicFunction) continue;
      expect(
        () => isDiatonic("C", name, parseChord("C7")),
        `${name} must refuse functional queries`,
      ).toThrow(NonFunctionalScaleError);
    }
  });

  it("membership (contains) still answers on non-functional scales", () => {
    const chromatic = Scales["Chromatic"]!;
    const wholeTone = Scales["WholeTone"]!;
    for (let pc = 0; pc < 12; pc++) {
      expect(contains(chromatic, pc), `Chromatic pc ${pc}`).toBe(true);
    }
    expect(contains(wholeTone, 0)).toBe(true);
    expect(contains(wholeTone, 1)).toBe(false);
  });
});
