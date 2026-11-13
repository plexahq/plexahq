import type { ChainRegistry } from "./chains.js";
import { compactMessage, scanGet } from "./layerzero.js";

/** Chains whose block height the website shows live. */
export const LIVE_CHAINS = ["ethereum", "base", "arbitrum", "hyperevm"] as const;

/** Zero mainnet launch as announced by LayerZero (date only; UTC midnight assumed). */
export const ZERO_MAINNET_AT = "2026-11-30T00:00:00Z";

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) => setTimeout(() => reject(new Error(`timed out after ${ms}ms`)), ms)),
  ]);
}

export interface LiveSnapshot {
  generatedAt: string;
  messages: ReturnType<typeof compactMessage>[];
  blocks: { chain: string; block: string | null }[];
  zero: { mainnetAt: string; rpcConfigured: boolean };
}

/**
 * A small, cache-friendly snapshot of what is happening on-chain right now:
 * the latest LayerZero messages and the head block of a few chains.
 * Every part fails soft so one slow upstream never blanks the whole feed.
 */
export async function getLiveSnapshot(registry: ChainRegistry, timeoutMs = 6000, messageCount = 16): Promise<LiveSnapshot> {
  const [messages, blocks] = await Promise.all([
    withTimeout(scanGet("mainnet", `/messages/latest?limit=${messageCount}`), timeoutMs)
      .then(({ data }) => data.map((m) => compactMessage(m, "mainnet")))
      .catch(() => []),
    Promise.all(
      LIVE_CHAINS.map(async (chain) => {
        try {
          const client = await registry.client(chain);
          const block = await withTimeout(client.getBlockNumber({ cacheTime: 0 }), timeoutMs);
          return { chain, block: block.toString() };
        } catch {
          return { chain, block: null };
        }
      }),
    ),
  ]);
  const zeroAtlas = registry.list().find((c) => c.key === "zero-atlas");
  return {
    generatedAt: new Date().toISOString(),
    messages,
    blocks,
    zero: { mainnetAt: ZERO_MAINNET_AT, rpcConfigured: Boolean(zeroAtlas?.rpcUrl) },
  };
}
