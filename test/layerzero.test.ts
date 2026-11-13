import { describe, expect, it } from "vitest";
import { findChains, summarizeChain, summarizeMessage, type LzMetadata, type ScanMessage } from "../src/layerzero.js";

const metadata: LzMetadata = {
  "base-mainnet": {
    chainKey: "base",
    chainDetails: { nativeChainId: 8453, name: "Base", chainStatus: "ACTIVE", nativeCurrency: { symbol: "ETH" } },
    deployments: [
      { version: 1, eid: "184" },
      { version: 2, eid: "30184", stage: "mainnet", endpointV2: { address: "0x1a44" } },
    ],
    dvns: {
      "0xa": { canonicalName: "LayerZero Labs" },
      "0xb": { canonicalName: "Old DVN", deprecated: true },
    },
    blockExplorers: [{ url: "https://basescan.org" }],
  },
  "zeroatlas-mainnet": {
    chainKey: "zeroatlas-mainnet-custom",
    chainDetails: { chainType: "evm", nativeCurrency: { symbol: "ZRO" } },
  },
  "zerointerop-mainnet": {
    chainKey: "zerointerop-mainnet-custom",
    chainDetails: { chainType: "evm", nativeCurrency: { symbol: "ZRO" } },
  },
};

describe("findChains", () => {
  it("matches by metadata key, chain key, EID and chain ID", () => {
    expect(findChains(metadata, "base-mainnet").exact?.metadataKey).toBe("base-mainnet");
    expect(findChains(metadata, "base").exact?.metadataKey).toBe("base-mainnet");
    expect(findChains(metadata, "30184").exact?.metadataKey).toBe("base-mainnet");
    expect(findChains(metadata, "8453").exact?.metadataKey).toBe("base-mainnet");
    expect(findChains(metadata, "zeroatlas-mainnet-custom").exact?.metadataKey).toBe("zeroatlas-mainnet");
  });

  it("falls back to substring search", () => {
    const { exact, matches } = findChains(metadata, "zero");
    expect(exact).toBeUndefined();
    expect(matches.map((m) => m.metadataKey)).toEqual(["zeroatlas-mainnet", "zerointerop-mainnet"]);
  });
});

describe("summarizeChain", () => {
  it("lists V2 deployments and only active DVNs", () => {
    const s = summarizeChain(findChains(metadata, "base").exact!);
    expect(s.layerZeroV2[0]?.eid).toBe(30184);
    expect(s.otherEids).toEqual([184]);
    expect(s.activeDvns).toEqual(["LayerZero Labs"]);
  });
});

describe("summarizeMessage", () => {
  const inflight: ScanMessage = {
    pathway: {
      srcEid: 30101,
      dstEid: 30184,
      sender: { address: "0xs", name: "Stargate", chain: "ethereum" },
      receiver: { address: "0xr", name: "Stargate", chain: "base" },
      nonce: 7,
    },
    source: { status: "SUCCEEDED", tx: { txHash: "0xabc", blockTimestamp: 1_800_000_000, from: "0xwallet" } },
    destination: { status: "WAITING", nativeDrop: { status: "N/A" }, lzCompose: { status: "N/A" } },
    verification: {
      dvn: { status: "WAITING", dvns: { "0xD1": { status: "SUCCEEDED" }, "0xd2": { status: "WAITING" } } },
    },
    config: {
      inboundConfig: { confirmations: 15, requiredDVNs: ["0xd1", "0xd2"], requiredDVNNames: ["LayerZero Labs", "Canary"] },
    },
    guid: "0xguid",
    status: { name: "INFLIGHT", message: "Source transaction sent" },
  };

  it("names DVNs and reports which ones are still pending", () => {
    const s = summarizeMessage(inflight, "mainnet");
    expect(s.status).toBe("INFLIGHT");
    expect(s.meaning).toMatch(/on its way/);
    expect(s.verification.dvns.map((d) => d.name)).toEqual(["LayerZero Labs", "Canary"]);
    expect(s.verification.waitingOn).toEqual(["Canary"]);
    expect(s.compose).toBeUndefined();
    expect(s.scanUrl).toBe("https://layerzeroscan.com/tx/0xabc");
  });

  it("computes delivery time and uses the testnet scan URL", () => {
    const delivered: ScanMessage = {
      ...inflight,
      destination: { status: "SUCCEEDED", tx: { txHash: "0xdst", blockTimestamp: 1_800_000_045 } },
      status: { name: "DELIVERED" },
    };
    const s = summarizeMessage(delivered, "testnet");
    expect(s.deliverySeconds).toBe(45);
    expect(s.verification.waitingOn).toBeUndefined();
    expect(s.scanUrl).toBe("https://testnet.layerzeroscan.com/tx/0xabc");
  });
});
