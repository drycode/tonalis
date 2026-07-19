import { describe, it, expect } from "vitest";
import { scaleValue, encodingValue, stripRight, stripLeft, semitonesApartAscending } from "./index.js";

describe("encode (BigInt layer)", () => {
  it("Scales constants are the 36-bit reference integers", () => {
    expect(scaleValue("Major")).toBe(46534580949n);
    expect(scaleValue("Minor")).toBe(48766495578n);
    expect(scaleValue("HarmonicMinor")).toBe(48749714265n);
  });
  it("encoding sets the sentinel bit and the triad/7th bits", () => {
    // Major triad + minor 7th (dominant): bits 18 (sentinel),14,11,8
    expect(encodingValue("Major", "Minor", [])).toBe(
      (1n << 18n) | (1n << 14n) | (1n << 11n) | (1n << 8n),
    );
    // Major triad alone (no 7th):
    expect(encodingValue("Major", "_None", [])).toBe((1n << 18n) | (1n << 14n) | (1n << 11n));
  });
  it("semitonesApartAscending matches the reference", () => {
    expect(semitonesApartAscending("C", "G")).toBe(7);
    expect(semitonesApartAscending("G", "C")).toBe(5);
  });
  it("strip helpers throw on the reference raise conditions", () => {
    expect(() => stripLeft(5n, 1)).toThrow();       // 5n < MIN_SUPPORTED
    expect(() => stripRight(262144n, 99)).toThrow(); // shift > bit-length
  });
});
