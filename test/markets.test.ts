import { describe, expect, it } from "vitest";
import { describeController, describeUln, dvnDirectory, overallRisk, verifiersNeeded, type UlnConfig } from "../src/lzsecurity.js";
import { findStocks, groupTokens } from "../src/stocks.js";
import { human } from "../src/tools/markets.js";

const LZ = "0x589dEDbD617e0CBcB916A9223F4d1300c294236b";
const GOOGLE = "0xD56e4eAb23cb81f43168F9F45211Eb027b9aC7cc";
const DEAD = "0x000000000000000000000000000000000000dEaD";
const dir = dvnDirectory(
  {
    chainKey: "ethereum",
    dvns: {
      [LZ.toLowerCase()]: { canonicalName: "LayerZero Labs", id: "layerzero-labs" },
      [GOOGLE.toLowerCase()]: { canonicalName: "Google", id: "google-cloud" },
      [DEAD.toLowerCase()]: { canonicalName: "LZDeadDVN", id: "lz-dead-dvn" },
    },
  },
  undefined,
);
const uln = (required: string[], optional: string[] = [], threshold = 0): UlnConfig => ({
  confirmations: 15n,
  requiredDVNCount: required.length,
  optionalDVNCount: optional.length,
  optionalDVNThreshold: threshold,
  requiredDVNs: required as `0x${string}`[],
  optionalDVNs: optional as `0x${string}`[],
});

describe("LayerZero security assessment", () => {
  it("counts required DVNs plus the optional threshold", () => {
    expect(verifiersNeeded(uln([LZ], [GOOGLE, DEAD], 1))).toBe(2);
  });

  it("names DVNs and accepts a two-DVN pathway", () => {
    const d = describeUln(uln([LZ, GOOGLE]), dir, "send", true);
    expect(d.requiredDVNs).toEqual(["LayerZero Labs", "Google"]);
    expect(d.summary).toMatch(/^2 DVN signatures needed/);
    expect(d.findings).toEqual([]);
  });

  it("flags a pathway one DVN can approve alone", () => {
    const d = describeUln(uln([LZ]), dir, "receive", true);
    expect(d.findings[0]?.severity).toBe("high");
    expect(d.findings[0]?.message).toContain("LayerZero Labs");
  });

  it("treats a dead DVN as a closed direction, not a risk", () => {
    const d = describeUln(uln([DEAD]), dir, "send", false);
    expect(d.summary).toBe("closed");
    expect(d.findings.map((f) => f.severity)).toEqual(["info"]);
  });

  it("notes default settings and unlisted DVNs", () => {
    const other = "0x1111111111111111111111111111111111111111";
    const d = describeUln(uln([LZ, other]), dir, "send", false);
    expect(d.requiredDVNs[1]).toMatch(/^unlisted DVN 0x1111/);
    expect(d.settings).toBe("LayerZero defaults");
    expect(d.findings[0]?.severity).toBe("info");
  });

  it("classifies who controls the app", () => {
    expect(describeController("0x").kind).toBe("single key");
    expect(describeController(`0xef0100${"ab".repeat(20)}`).kind).toBe("single key");
    expect(describeController("0x6080", { threshold: 3n, owners: 5 }).detail).toContain("3 of 5");
    expect(describeController("0x6080").kind).toBe("contract");
  });

  it("rolls findings up into one risk level", () => {
    expect(overallRisk([])).toBe("low");
    expect(overallRisk([{ severity: "info", message: "" }, { severity: "medium", message: "" }])).toBe("medium");
    expect(overallRisk([{ severity: "high", message: "" }])).toBe("high");
  });
});

describe("tokenized stocks", () => {
  const tokens = groupTokens([
    { chainId: 1, address: "0x14c3abf95cb9c93a8b82c1cdcb76d72cb87b2d4c", name: "Apple (Ondo Tokenized)", symbol: "AAPLon", decimals: 18 },
    { chainId: 56, address: "0x390a684EF9cADE28A7AD0DFa61AB1Eb3842618c4", name: "Apple (Ondo Tokenized)", symbol: "AAPLon", decimals: 18 },
    { chainId: 1, address: "0xFeDC5f4a6c38211c1338aa411018DFAf26612c08", name: "SPDR S&P 500 ETF (Ondo Tokenized)", symbol: "SPYon", decimals: 18 },
    { chainId: 1, address: "0xAcE8E719899F6E91831B18AE746C9A965c2119F1", name: "Ondo U.S. Dollar Token", symbol: "USDon", decimals: 18 },
    { chainId: 137, address: "0x0000000000000000000000000000000000000001", name: "Ignored", symbol: "Xon", decimals: 18 },
  ]);

  it("groups list entries per symbol and chain, with checksummed addresses", () => {
    expect(tokens).toHaveLength(3);
    const aapl = tokens.find((t) => t.symbol === "AAPLon")!;
    expect(aapl).toMatchObject({ ticker: "AAPL", name: "Apple", kind: "stock or ETF" });
    expect(aapl.addresses.ethereum).toBe("0x14c3abF95Cb9C93a8b82C1CdCB76D72Cb87b2d4c");
    expect(aapl.addresses.bnb).toBeDefined();
    expect(tokens.find((t) => t.symbol === "USDon")?.kind).toBe("cash");
  });

  it("finds by ticker, symbol, $ticker or name", () => {
    expect(findStocks(tokens, "aapl")[0]?.symbol).toBe("AAPLon");
    expect(findStocks(tokens, "$AAPL")[0]?.symbol).toBe("AAPLon");
    expect(findStocks(tokens, "SPYon")[0]?.symbol).toBe("SPYon");
    expect(findStocks(tokens, "s&p 500")[0]?.symbol).toBe("SPYon");
    expect(findStocks(tokens, "nothing here")).toEqual([]);
  });
});

describe("amount formatting", () => {
  it("groups thousands and trims decimals", () => {
    expect(human(951082492878414000000000000n, 18)).toBe("951,082,492.87");
    expect(human(10n ** 18n, 18)).toBe("1");
    expect(human(257_900_000_000_000_000n, 18, 4)).toBe("0.2579");
  });
});
