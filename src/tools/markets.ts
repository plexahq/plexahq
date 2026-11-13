import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { erc20Abi, formatUnits, getAddress, type Address } from "viem";
import { z } from "zod";
import { explorerAddressUrl, type ChainRegistry } from "../chains.js";
import { ZERO_MAINNET_AT } from "../live.js";
import { errorMessage, safe } from "../result.js";
import { findStocks, getStockTokens, STOCK_CHAINS, type StockToken } from "../stocks.js";

const READ_ONLY = { readOnlyHint: true, destructiveHint: false, openWorldHint: true } as const;
const address = z.string().regex(/^0x[0-9a-fA-F]{40}$/, "Must be a 0x-prefixed 20-byte address");

/** ZRO is a LayerZero OFT deployed at the same address on every chain below. */
export const ZRO_ADDRESS: Address = "0x6985884C4392D348587B19cb9eAAf157F13271cd";
export const ZRO_CHAINS = ["ethereum", "arbitrum", "base", "bnb", "optimism", "polygon", "avalanche"] as const;
const ZRO_MAX_SUPPLY = 1_000_000_000n * 10n ** 18n;
const CHAIN_TIMEOUT_MS = 15_000;

function withTimeout<T>(p: Promise<T>, ms = CHAIN_TIMEOUT_MS): Promise<T> {
  return Promise.race([p, new Promise<T>((_, rej) => setTimeout(() => rej(new Error(`timed out after ${ms / 1000}s`)), ms))]);
}

/** 1234567.891 → "1,234,567.89" */
export function human(raw: bigint, decimals: number, digits = 2): string {
  const [int, frac = ""] = formatUnits(raw, decimals).split(".");
  const grouped = int!.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const f = frac.slice(0, digits).replace(/0+$/, "");
  return f ? `${grouped}.${f}` : grouped;
}

function pct(part: bigint, whole: bigint): string {
  if (whole === 0n) return "0%";
  return `${(Number((part * 10_000n) / whole) / 100).toFixed(2)}%`;
}

export function registerMarketTools(server: McpServer, registry: ChainRegistry): void {
  server.registerTool(
    "zro_overview",
    {
      title: "ZRO across chains",
      description:
        "Shows where LayerZero's ZRO token lives: its supply on each chain, read live from the ZRO contracts. With a wallet address it also returns that wallet's ZRO on every chain and whether it is ready for Zero, where ZRO pays for gas.",
      inputSchema: {
        address: address.optional().describe("Optional wallet to check for ZRO on every chain"),
      },
      annotations: READ_ONLY,
    },
    safe(async ({ address: addr }) => {
      const wallet = addr ? getAddress(addr) : undefined;
      const rows = await Promise.all(
        ZRO_CHAINS.map(async (key) => {
          const cfg = registry.get(key);
          try {
            const client = await registry.client(key);
            const calls = [
              { address: ZRO_ADDRESS, abi: erc20Abi, functionName: "totalSupply" },
              ...(wallet ? [{ address: ZRO_ADDRESS, abi: erc20Abi, functionName: "balanceOf", args: [wallet] }] : []),
            ];
            const res = await withTimeout(client.multicall({ contracts: calls as never, allowFailure: false }));
            const [supply, balance] = res as bigint[];
            return { key, name: cfg.name, supply: supply!, balance, explorer: explorerAddressUrl(cfg, ZRO_ADDRESS) };
          } catch (error) {
            return { key, name: cfg.name, error: errorMessage(error) };
          }
        }),
      );
      const okRows = rows.filter((r): r is Extract<typeof r, { supply: bigint }> => "supply" in r);
      const total = okRows.reduce((s, r) => s + r.supply, 0n);
      const unavailable = rows.filter((r) => "error" in r).map((r) => ({ chain: r.name, error: (r as { error: string }).error }));
      const zero = registry.list().filter((c) => c.key.startsWith("zero-"));
      const zeroLive = zero.some((c) => c.rpcUrl);

      const out: Record<string, unknown> = {
        token: "ZRO (LayerZero)",
        contract: ZRO_ADDRESS,
        sameAddressOn: ZRO_CHAINS.map((k) => registry.get(k).name),
        howItMoves: "ZRO is a LayerZero OFT: moving it burns it on one chain and mints it on the other, so the supplies below add up to the total.",
        supply: {
          maxSupply: human(ZRO_MAX_SUPPLY, 18, 0),
          countedOnTheseChains: human(total, 18),
          notOnTheseChains:
            unavailable.length === 0 && total < ZRO_MAX_SUPPLY
              ? `${human(ZRO_MAX_SUPPLY - total, 18)} ZRO sits on other chains or has been burned.`
              : undefined,
          byChain: okRows
            .sort((a, b) => (b.supply > a.supply ? 1 : b.supply < a.supply ? -1 : 0))
            .map((r) => ({ chain: r.name, supply: human(r.supply, 18), share: pct(r.supply, total), explorer: r.explorer })),
          unavailable: unavailable.length ? unavailable : undefined,
        },
        zero: {
          role: "LayerZero has said ZRO will be Zero's gas and staking token.",
          mainnet: ZERO_MAINNET_AT.slice(0, 10),
          status: zeroLive ? "Zero RPC configured in Plexa." : "Zero's public RPC and chain IDs are not published yet (tba).",
        },
      };

      if (wallet) {
        const held = okRows.filter((r) => (r.balance ?? 0n) > 0n);
        const sum = okRows.reduce((s, r) => s + (r.balance ?? 0n), 0n);
        out.wallet = {
          address: wallet,
          totalZro: human(sum, 18, 4),
          byChain: held.map((r) => ({ chain: r.name, zro: human(r.balance!, 18, 4) })),
          zeroReadiness:
            sum > 0n
              ? `Holds ${human(sum, 18, 4)} ZRO on ${held.map((r) => r.name).join(", ")}. Zero gas is paid in ZRO, so this wallet can cover transactions on Zero once it moves some ZRO there over LayerZero (after mainnet).`
              : "No ZRO on these chains. Transactions on Zero are paid in ZRO, so this wallet would need some first.",
        };
        if (unavailable.length) (out.wallet as Record<string, unknown>).note = "Some chains could not be read; the total may be incomplete.";
      }
      return out;
    }),
  );

  server.registerTool(
    "stocks_lookup",
    {
      title: "Tokenized stock lookup",
      description:
        "Finds a tokenized stock or ETF (Ondo Global Markets, e.g. AAPLon for Apple) by ticker or name, and reads its live token supply on each chain plus contract addresses. Ondo moves these tokens between chains with LayerZero. Supply only: no prices.",
      inputSchema: {
        query: z.string().min(1).max(60).describe('Ticker or name, e.g. "AAPL", "NVDA", "Tesla" or "S&P 500"'),
      },
      annotations: READ_ONLY,
    },
    safe(async ({ query }) => {
      const tokens = await getStockTokens();
      const matches = findStocks(tokens, query);
      if (matches.length === 0) {
        return { found: false, message: `No tokenized stock or ETF matches "${query}". Ondo lists ${tokens.length} tokens; try a ticker like AAPL or a company name.` };
      }
      const supplies = await readMany(registry, matches, "totalSupply");
      return {
        found: matches.length,
        issuer: "Ondo Global Markets",
        matches: matches.map((t) => {
          let total = 0n;
          const chains = Object.entries(t.addresses).map(([key, addr]) => {
            const cfg = registry.get(key);
            const s = supplies.get(`${key}:${addr.toLowerCase()}`);
            if (typeof s === "bigint") total += s;
            return {
              chain: cfg.name,
              address: addr,
              supply: typeof s === "bigint" ? human(s, t.decimals) : undefined,
              error: typeof s === "string" ? s : undefined,
              explorer: explorerAddressUrl(cfg, addr),
            };
          });
          return { symbol: t.symbol, ticker: t.ticker, name: t.name, kind: t.kind, totalTokens: human(total, t.decimals), chains };
        }),
        note: "Token counts read from the chain. Plexa only reads public data; it does not offer, price or trade these tokens.",
      };
    }),
  );

  server.registerTool(
    "stocks_portfolio",
    {
      title: "Tokenized stock holdings",
      description:
        "Lists every tokenized stock and ETF (Ondo Global Markets) a wallet holds on Ethereum and BNB Chain, read live from the chain in a few batched calls. Amounts only: no prices.",
      inputSchema: {
        address: address.describe("Wallet or contract address"),
        limit: z.number().int().min(1).max(500).optional().describe("Max holdings to list (default 50); positions always gives the full count"),
      },
      annotations: READ_ONLY,
    },
    safe(async ({ address: addr, limit }) => {
      const wallet = getAddress(addr);
      const max = limit ?? 50;
      const tokens = await getStockTokens();
      const balances = await readMany(registry, tokens, "balanceOf", wallet);
      const holdings: { symbol: string; name: string; chain: string; amount: string }[] = [];
      for (const t of tokens) {
        for (const [key, a] of Object.entries(t.addresses)) {
          const b = balances.get(`${key}:${a.toLowerCase()}`);
          if (typeof b === "bigint" && b > 0n) holdings.push({ symbol: t.symbol, name: t.name, chain: registry.get(key).name, amount: human(b, t.decimals, 4) });
        }
      }
      holdings.sort((x, y) => x.symbol.localeCompare(y.symbol));
      const failed = [...new Set([...balances.entries()].filter(([, v]) => typeof v === "string").map(([k]) => registry.get(k.split(":")[0]!).name))];
      return {
        address: wallet,
        positions: holdings.length,
        holdings: holdings.slice(0, max),
        truncated: holdings.length > max ? `Showing ${max} of ${holdings.length} positions (alphabetical). Raise limit to see more.` : undefined,
        checked: `${tokens.length} Ondo tokens on ${Object.values(STOCK_CHAINS).map((k) => registry.get(k).name).join(" and ")}`,
        unreadable: failed.length ? failed : undefined,
        note: "Token amounts read from the chain; no prices. Plexa only reads public data.",
      };
    }),
  );
}

/**
 * Reads totalSupply or balanceOf for many stock tokens, batched per chain.
 * Returns "chain:address" → value, or an error string when that chain failed.
 */
async function readMany(registry: ChainRegistry, tokens: StockToken[], fn: "totalSupply" | "balanceOf", owner?: Address) {
  const out = new Map<string, bigint | string>();
  const perChain = new Map<string, `0x${string}`[]>();
  for (const t of tokens) for (const [k, a] of Object.entries(t.addresses)) perChain.set(k, [...(perChain.get(k) ?? []), a]);
  await Promise.all(
    [...perChain.entries()].map(async ([key, addrs]) => {
      try {
        const client = await registry.client(key);
        const res = (await withTimeout(
          client.multicall({
            contracts: addrs.map((a) => ({ address: a, abi: erc20Abi, functionName: fn, args: fn === "balanceOf" ? [owner!] : [] })) as never,
            allowFailure: true,
            batchSize: 24_000,
          }),
          25_000,
        )) as unknown as { status: "success" | "failure"; result?: unknown }[];
        res.forEach((r, i) => out.set(`${key}:${addrs[i]!.toLowerCase()}`, r.status === "success" ? (r.result as bigint) : "unreadable"));
      } catch (error) {
        for (const a of addrs) out.set(`${key}:${a.toLowerCase()}`, errorMessage(error));
      }
    }),
  );
  return out;
}
