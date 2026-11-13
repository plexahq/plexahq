import { describe, expect, it } from "vitest";
import { ChainRegistry, envSuffix, loadChains } from "../src/chains.js";

describe("loadChains", () => {
  it("ships Zero zones as placeholders without RPC", () => {
    const chains = loadChains({});
    const atlas = chains.find((c) => c.key === "zero-atlas");
    expect(atlas).toBeDefined();
    expect(atlas?.rpcUrl).toBeUndefined();
    expect(atlas?.nativeSymbol).toBe("ZRO");
  });

  it("applies RPC, chain ID and explorer overrides from env", () => {
    const chains = loadChains({
      PLEXA_RPC_ZERO_ATLAS: "https://rpc.example.org",
      PLEXA_CHAIN_ID_ZERO_ATLAS: "12345",
      PLEXA_EXPLORER_ZERO_ATLAS: "https://explorer.example.org/",
    });
    const atlas = chains.find((c) => c.key === "zero-atlas")!;
    expect(atlas.rpcUrl).toBe("https://rpc.example.org");
    expect(atlas.chainId).toBe(12345);
    expect(atlas.explorerUrl).toBe("https://explorer.example.org");
  });

  it("rejects an invalid chain ID", () => {
    expect(() => loadChains({ PLEXA_CHAIN_ID_BASE: "abc" })).toThrow(/positive integer/);
  });

  it("adds extra chains from PLEXA_EXTRA_CHAINS", () => {
    const chains = loadChains({
      PLEXA_EXTRA_CHAINS: JSON.stringify([{ key: "mychain", name: "My Chain", chainId: 777, rpcUrl: "https://x" }]),
    });
    const extra = chains.find((c) => c.key === "mychain")!;
    expect(extra.chainId).toBe(777);
    expect(extra.nativeSymbol).toBe("ETH");
  });

  it("rejects duplicate keys", () => {
    expect(() => loadChains({ PLEXA_EXTRA_CHAINS: JSON.stringify([{ key: "base", name: "Dup" }]) })).toThrow(/Duplicate/);
  });
});

describe("ChainRegistry", () => {
  const registry = new ChainRegistry(loadChains({}));

  it("looks chains up by key and by chain ID", () => {
    expect(registry.get("base").chainId).toBe(8453);
    expect(registry.get("8453").key).toBe("base");
    expect(registry.get(" BASE ").key).toBe("base");
  });

  it("throws a helpful error for unknown chains", () => {
    expect(() => registry.get("nope")).toThrow(/Known chains/);
  });

  it("explains how to enable a chain without RPC", async () => {
    await expect(registry.client("zero-atlas")).rejects.toThrow(/PLEXA_RPC_ZERO_ATLAS/);
  });
});

describe("envSuffix", () => {
  it("normalizes keys", () => {
    expect(envSuffix("zero-atlas")).toBe("ZERO_ATLAS");
    expect(envSuffix("base-sepolia")).toBe("BASE_SEPOLIA");
  });
});
