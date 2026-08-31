import { describe, expect, it } from "vitest";
import { gcj02ToWgs84 } from "./SpotsMap";

describe("gcj02ToWgs84", () => {
  it("converts a China GCJ-02 point for OpenStreetMap", () => {
    const [lat, lon] = gcj02ToWgs84(30.27415, 120.15515);
    expect(lat).toBeCloseTo(30.2765, 2);
    expect(lon).toBeCloseTo(120.1505, 2);
  });

  it("keeps overseas coordinates unchanged", () => {
    expect(gcj02ToWgs84(40.7128, -74.006)).toEqual([40.7128, -74.006]);
  });
});
