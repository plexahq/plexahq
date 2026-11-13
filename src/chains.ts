import { createPublicClient, defineChain, http, type Chain, type PublicClient } from "viem";

/**
 * A chain Plexa knows about.
 *
 * `chainId` and `rpcUrl` are optional on purpose: LayerZero has not yet published
 * public RPCs or chain IDs for Zero mainnet, so those chains ship as placeholders
 * that become usable once an RPC URL is supplied via environment variables.
 */
export interface ChainConfig {
  /** Stable identifier used in tool calls, e.g. "base" or "zero-atlas". */
  key: string;
  name: string;
  chainId?: number;
  testnet: boolean;
  nativeSymbol: string;
  nativeDecimals: number;
  rpcUrl?: string;
  explorerUrl?: string;
  /** LayerZero V2 endpoint ID, when known. */
  lzEid?: number;
  /** Chain key used by the LayerZero metadata and Scan APIs. */
  lzChainKey?: string;
  /** LayerZero EndpointV2 contract address, when known. */
  lzEndpointV2?: `0x${string}`;
  notes?: string;
}

const LZ_ENDPOINT_V2_MAINNET = "0x1a44076050125825900e736c501f859c50fe728c";
const LZ_ENDPOINT_V2_TESTNET = "0x6edce65403992e310a62460808c4b910d972f10f";

/**
 * Built-in chains. EIDs, endpoint addresses and explorers were taken from
 * https://metadata.layerzero-api.com/v1/metadata/deployments.
 */
export const BUILTIN_CHAINS: readonly ChainConfig[] = [
  {
    key: "zero-atlas",
    name: "Zero (ATLAS zone)",
    testnet: false,
    nativeSymbol: "ZRO",
    nativeDecimals: 18,
    lzChainKey: "zeroatlas-mainnet-custom",
    notes:
      "LayerZero Zero trading zone (lzATLAS). Mainnet launches 2026-11-30; set PLEXA_RPC_ZERO_ATLAS to enable.",
  },
  {
    key: "zero-interop",
    name: "Zero (Interop zone)",
    testnet: false,
    nativeSymbol: "ZRO",
    nativeDecimals: 18,
    lzChainKey: "zerointerop-mainnet-custom",
    notes:
      "LayerZero Zero interop zone. Mainnet launches 2026-11-30; set PLEXA_RPC_ZERO_INTEROP to enable.",
  },
  {
    key: "ethereum",
    name: "Ethereum",
    chainId: 1,
    testnet: false,
    nativeSymbol: "ETH",
    nativeDecimals: 18,
    rpcUrl: "https://ethereum-rpc.publicnode.com",
    explorerUrl: "https://etherscan.io",
    lzEid: 30101,
    lzChainKey: "ethereum",
    lzEndpointV2: LZ_ENDPOINT_V2_MAINNET,
  },
  {
    key: "arbitrum",
    name: "Arbitrum One",
    chainId: 42161,
    testnet: false,
    nativeSymbol: "ETH",
    nativeDecimals: 18,
    rpcUrl: "https://arb1.arbitrum.io/rpc",
    explorerUrl: "https://arbiscan.io",
    lzEid: 30110,
    lzChainKey: "arbitrum",
    lzEndpointV2: LZ_ENDPOINT_V2_MAINNET,
  },
  {
    key: "base",
    name: "Base",
    chainId: 8453,
    testnet: false,
    nativeSymbol: "ETH",
    nativeDecimals: 18,
    rpcUrl: "https://mainnet.base.org",
    explorerUrl: "https://basescan.org",
    lzEid: 30184,
    lzChainKey: "base",
    lzEndpointV2: LZ_ENDPOINT_V2_MAINNET,
  },
  {
    key: "hyperevm",
    name: "HyperEVM",
    chainId: 999,
    testnet: false,
    nativeSymbol: "HYPE",
    nativeDecimals: 18,
    rpcUrl: "https://rpc.hyperliquid.xyz/evm",
    explorerUrl: "https://hyperevmscan.io",
    lzEid: 30367,
    lzChainKey: "hyperliquid",
    lzEndpointV2: "0x3a73033c0b1407574c76bdbac67f126f6b4a9aa9",
  },
  {
    key: "ethereum-sepolia",
    name: "Ethereum Sepolia",
    chainId: 11155111,
    testnet: true,
    nativeSymbol: "ETH",
    nativeDecimals: 18,
    rpcUrl: "https://ethereum-sepolia-rpc.publicnode.com",
    explorerUrl: "https://sepolia.etherscan.io",
    lzEid: 40161,
    lzChainKey: "sepolia-testnet",
    lzEndpointV2: LZ_ENDPOINT_V2_TESTNET,
  },
  {
    key: "arbitrum-sepolia",
    name: "Arbitrum Sepolia",
    chainId: 421614,
    testnet: true,
    nativeSymbol: "ETH",
    nativeDecimals: 18,
    rpcUrl: "https://sepolia-rollup.arbitrum.io/rpc",
    explorerUrl: "https://sepolia.arbiscan.io",
    lzEid: 40231,
    lzChainKey: "arbitrum-sepolia",
    lzEndpointV2: LZ_ENDPOINT_V2_TESTNET,
  },
  {
    key: "base-sepolia",
    name: "Base Sepolia",
    chainId: 84532,
    testnet: true,
    nativeSymbol: "ETH",
    nativeDecimals: 18,
    rpcUrl: "https://sepolia.base.org",
    explorerUrl: "https://sepolia.basescan.org",
    lzEid: 40245,
    lzChainKey: "base-sepolia",
    lzEndpointV2: LZ_ENDPOINT_V2_TESTNET,
  },
];

type Env = Record<string, string | undefined>;

/** "zero-atlas" -> "ZERO_ATLAS" */
export function envSuffix(key: string): string {
  return key.toUpperCase().replace(/[^A-Z0-9]+/g, "_");
}

/**
 * Applies environment overrides to the built-in chain list:
 *  - PLEXA_RPC_<KEY>           replaces or sets the RPC URL
 *  - PLEXA_CHAIN_ID_<KEY>      sets the chain ID (otherwise read from the RPC)
 *  - PLEXA_EXPLORER_<KEY>      sets the block explorer URL
 *  - PLEXA_EXTRA_CHAINS        JSON array of extra ChainConfig objects
 */
export function loadChains(env: Env = process.env): ChainConfig[] {
  const extra: ChainConfig[] = env.PLEXA_EXTRA_CHAINS ? parseExtraChains(env.PLEXA_EXTRA_CHAINS) : [];
  const all = [...BUILTIN_CHAINS.map((c) => ({ ...c })), ...extra];

  const seen = new Set<string>();
  for (const chain of all) {
    if (seen.has(chain.key)) throw new Error(`Duplicate chain key: ${chain.key}`);
    seen.add(chain.key);

    const suffix = envSuffix(chain.key);
    const rpc = env[`PLEXA_RPC_${suffix}`];
    if (rpc) chain.rpcUrl = rpc;
    const id = env[`PLEXA_CHAIN_ID_${suffix}`];
    if (id) {
      const n = Number(id);
      if (!Number.isInteger(n) || n <= 0) throw new Error(`PLEXA_CHAIN_ID_${suffix} must be a positive integer`);
      chain.chainId = n;
    }
    const explorer = env[`PLEXA_EXPLORER_${suffix}`];
    if (explorer) chain.explorerUrl = explorer.replace(/\/+$/, "");
  }
  return all;
}

function parseExtraChains(raw: string): ChainConfig[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error("PLEXA_EXTRA_CHAINS is not valid JSON");
  }
  if (!Array.isArray(parsed)) throw new Error("PLEXA_EXTRA_CHAINS must be a JSON array");
  return parsed.map((c, i) => {
    if (typeof c !== "object" || c === null) throw new Error(`PLEXA_EXTRA_CHAINS[${i}] must be an object`);
    const o = c as Partial<ChainConfig>;
    if (!o.key || !o.name) throw new Error(`PLEXA_EXTRA_CHAINS[${i}] needs "key" and "name"`);
    return {
      testnet: false,
      nativeSymbol: "ETH",
      nativeDecimals: 18,
      ...o,
    } as ChainConfig;
  });
}

export class ChainRegistry {
  private readonly chains: Map<string, ChainConfig>;
  private readonly clients = new Map<string, Promise<PublicClient>>();

  constructor(chains: ChainConfig[]) {
    this.chains = new Map(chains.map((c) => [c.key, c]));
  }

  list(): ChainConfig[] {
    return [...this.chains.values()];
  }

  keys(): string[] {
    return [...this.chains.keys()];
  }

  /** Looks a chain up by key, or by numeric chain ID given as a string. */
  get(keyOrId: string): ChainConfig {
    const direct = this.chains.get(keyOrId.trim().toLowerCase());
    if (direct) return direct;
    const asId = Number(keyOrId);
    if (Number.isInteger(asId)) {
      const byId = this.list().find((c) => c.chainId === asId);
      if (byId) return byId;
    }
    throw new Error(`Unknown chain "${keyOrId}". Known chains: ${this.keys().join(", ")}`);
  }

  findByLzChainKey(lzChainKey: string): ChainConfig | undefined {
    return this.list().find((c) => c.lzChainKey === lzChainKey);
  }

  findByEid(eid: number): ChainConfig | undefined {
    return this.list().find((c) => c.lzEid === eid);
  }

  /** Returns a viem client for the chain, resolving the chain ID from the RPC when needed. */
  client(keyOrId: string): Promise<PublicClient> {
    const chain = this.get(keyOrId);
    let pending = this.clients.get(chain.key);
    if (!pending) {
      pending = this.createClient(chain);
      this.clients.set(chain.key, pending);
      pending.catch(() => this.clients.delete(chain.key));
    }
    return pending;
  }

  private async createClient(chain: ChainConfig): Promise<PublicClient> {
    if (!chain.rpcUrl) {
      throw new Error(
        `${chain.name} has no RPC configured yet. Set PLEXA_RPC_${envSuffix(chain.key)} to enable it.` +
          (chain.notes ? ` (${chain.notes})` : ""),
      );
    }
    const transport = http(chain.rpcUrl, { timeout: 20_000, retryCount: 2 });
    if (chain.chainId === undefined) {
      const probe = createPublicClient({ transport });
      chain.chainId = await probe.getChainId();
    }
    return createPublicClient({ chain: toViemChain(chain), transport }) as PublicClient;
  }
}

export function toViemChain(chain: ChainConfig): Chain {
  if (chain.chainId === undefined || !chain.rpcUrl) {
    throw new Error(`Chain ${chain.key} is missing a chain ID or RPC URL`);
  }
  return defineChain({
    id: chain.chainId,
    name: chain.name,
    nativeCurrency: { name: chain.nativeSymbol, symbol: chain.nativeSymbol, decimals: chain.nativeDecimals },
    rpcUrls: { default: { http: [chain.rpcUrl] } },
    blockExplorers: chain.explorerUrl ? { default: { name: "Explorer", url: chain.explorerUrl } } : undefined,
    testnet: chain.testnet,
  });
}

export function explorerTxUrl(chain: ChainConfig, hash: string): string | undefined {
  return chain.explorerUrl ? `${chain.explorerUrl}/tx/${hash}` : undefined;
}

export function explorerAddressUrl(chain: ChainConfig, address: string): string | undefined {
  return chain.explorerUrl ? `${chain.explorerUrl}/address/${address}` : undefined;
}
