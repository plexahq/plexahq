/**
 * Live tests against real chains and LayerZero APIs. Skipped unless PLEXA_LIVE=1.
 *   npm run test:live
 * Behind an HTTP proxy, Node's fetch also needs NODE_USE_ENV_PROXY=1.
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createServer } from "../src/server.js";

const LIVE = process.env.PLEXA_LIVE === "1";
const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const VITALIK = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045";
const MAX = "f".repeat(64);
const pad = (hex: string) => hex.replace(/^0x/, "").toLowerCase().padStart(64, "0");

describe.skipIf(!LIVE)("live tools", { timeout: 60_000 }, () => {
  const client = new Client({ name: "plexa-live-test", version: "0.0.0" });

  beforeAll(async () => {
    const [clientT, serverT] = InMemoryTransport.createLinkedPair();
    await createServer().connect(serverT);
    await client.connect(clientT);
  });
  afterAll(() => client.close());

  async function call(name: string, args: Record<string, unknown>) {
    const res = (await client.callTool({ name, arguments: args })) as { isError?: boolean; content: { text: string }[] };
    const text = res.content[0]?.text ?? "";
    if (res.isError) throw new Error(`${name} failed: ${text}`);
    return JSON.parse(text);
  }

  it("reads native and token balances", async () => {
    const r = await call("get_balance", { chain: "base", address: VITALIK, tokens: [USDC_BASE] });
    expect(r.native.symbol).toBe("ETH");
    expect(r.tokens[0].symbol).toBe("USDC");
  });

  it("inspects a verified proxy contract", async () => {
    const r = await call("get_contract_info", { chain: "base", address: USDC_BASE });
    expect(r.verified).toBe(true);
    expect(r.proxy.implementationVerified).toBe(true);
    expect(r.readFunctions.some((f: string) => f.includes("balanceOf"))).toBe(true);
  });

  it("flags unlimited approvals to a non-contract spender", async () => {
    const r = await call("simulate_transaction", {
      chain: "base",
      to: USDC_BASE,
      from: VITALIK,
      data: `0x095ea7b3${pad("0xdead")}${MAX}`,
    });
    expect(r.wouldSucceed).toBe(true);
    expect(r.explanation).toMatch(/unlimited/);
    expect(r.warnings.join(" ")).toMatch(/phishing/);
  });

  it("reports a revert with its reason", async () => {
    // Transferring more than the total supply reverts for any sender.
    const r = await call("simulate_transaction", {
      chain: "base",
      to: USDC_BASE,
      from: VITALIK,
      data: `0xa9059cbb${pad("0xdead")}${MAX}`,
    });
    expect(r.wouldSucceed).toBe(false);
    expect(r.revertReason).toBeTruthy();
  });

  it("treats EIP-7702 delegated wallets as wallets", async () => {
    const sim = await call("simulate_transaction", { chain: "base", to: VITALIK, from: VITALIK, value: "0.001" });
    expect(sim.explanation).toMatch(/^Sends 0.001 ETH to the wallet/);
    const info = await call("get_contract_info", { chain: "base", address: VITALIK });
    expect(info.isContract).toBe(false);
  });

  it("finds Zero in LayerZero metadata", async () => {
    const r = await call("lz_chain_info", { query: "zero" });
    expect(JSON.stringify(r)).toMatch(/zeroatlas/);
  });

  it("lists the latest LayerZero messages", async () => {
    const r = await call("lz_latest_messages", { limit: 3 });
    expect(r.count).toBeGreaterThan(0);
    expect(r.messages[0].route).toContain("->");
  });

  it("tracks the latest LayerZero message", async () => {
    const latest = (await fetch("https://scan.layerzero-api.com/v1/messages/latest?limit=1").then((x) => x.json())) as {
      data: { source: { tx: { txHash: string } } }[];
    };
    const r = await call("lz_track_message", { txHash: latest.data[0]!.source.tx.txHash });
    expect(r.found).toBe(true);
    expect(r.messages[0].status).toBeTruthy();
  });
});
