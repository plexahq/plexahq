import { getAddress } from "viem";

/**
 * Tokenized stocks and ETFs (Ondo Global Markets), read from Ondo's public token list
 * and straight from the chain. Supply and balances only: no prices, no trading.
 */

const TOKENLIST_URL =
  process.env.PLEXA_ONDO_TOKENLIST_URL ??
  "https://raw.githubusercontent.com/ondoprotocol/ondo-global-markets-token-list/main/tokenlist.json";
const TTL_MS = 6 * 60 * 60 * 1000;

/** Ondo token-list chain IDs → Plexa chain keys. */
export const STOCK_CHAINS: Record<number, string> = { 1: "ethereum", 56: "bnb" };

export interface OndoListToken {
  chainId: number;
  address: string;
  name: string;
  symbol: string;
  decimals: number;
  logoURI?: string;
}

export interface StockToken {
  symbol: string;
  /** Underlying ticker, e.g. AAPL for AAPLon. */
  ticker: string;
  /** Underlying name without the "(Ondo Tokenized)" suffix. */
  name: string;
  kind: "stock or ETF" | "cash";
  decimals: number;
  /** Plexa chain key → token address. */
  addresses: Record<string, `0x${string}`>;
}

let cache: { at: number; data: Promise<StockToken[]> } | undefined;

export function getStockTokens(fetchImpl: typeof fetch = fetch): Promise<StockToken[]> {
  const now = Date.now();
  if (!cache || now - cache.at > TTL_MS) {
    const data = fetchImpl(TOKENLIST_URL, { signal: AbortSignal.timeout(20_000) }).then(async (res) => {
      if (!res.ok) throw new Error(`Ondo token list returned HTTP ${res.status}`);
      const body = (await res.json()) as { tokens?: OndoListToken[] };
      return groupTokens(body.tokens ?? []);
    });
    cache = { at: now, data };
    data.catch(() => {
      cache = undefined;
    });
  }
  return cache.data;
}

export function groupTokens(list: OndoListToken[]): StockToken[] {
  const bySymbol = new Map<string, StockToken>();
  for (const t of list) {
    const chain = STOCK_CHAINS[t.chainId];
    if (!chain || !/^0x[0-9a-fA-F]{40}$/.test(t.address)) continue;
    let s = bySymbol.get(t.symbol);
    if (!s) {
      const cash = /^USDon$/i.test(t.symbol);
      s = {
        symbol: t.symbol,
        ticker: t.symbol.replace(/on$/, ""),
        name: t.name.replace(/\s*\(Ondo Tokenized\)\s*$/i, "").trim(),
        kind: cash ? "cash" : "stock or ETF",
        decimals: t.decimals,
        addresses: {},
      };
      bySymbol.set(t.symbol, s);
    }
    // some list entries carry a broken EIP-55 checksum; normalise from lowercase
    s.addresses[chain] = getAddress(t.address.toLowerCase());
  }
  return [...bySymbol.values()];
}

/** Finds tokens by ticker ("AAPL", "aaplon") first, then by name ("apple", "s&p 500"). */
export function findStocks(tokens: StockToken[], query: string, limit = 5): StockToken[] {
  const q = query.trim().toLowerCase().replace(/^\$/, "");
  if (!q) return [];
  const exact = tokens.filter((t) => t.ticker.toLowerCase() === q || t.symbol.toLowerCase() === q);
  if (exact.length) return exact.slice(0, limit);
  const words = q.split(/\s+/);
  const byName = tokens.filter((t) => words.every((w) => t.name.toLowerCase().includes(w)));
  byName.sort((a, b) => a.name.length - b.name.length);
  return byName.slice(0, limit);
}
