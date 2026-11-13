/**
 * Thin clients for LayerZero's public metadata and Scan APIs.
 * Docs: https://docs.layerzero.network/v2/tools/api/scan/mainnet
 */

const METADATA_URL =
  process.env.PLEXA_LZ_METADATA_URL ?? "https://metadata.layerzero-api.com/v1/metadata/deployments";
const METADATA_TTL_MS = 60 * 60 * 1000;

export type LzNetwork = "mainnet" | "testnet";

const SCAN_API: Record<LzNetwork, string> = {
  mainnet: process.env.PLEXA_LZ_SCAN_URL ?? "https://scan.layerzero-api.com/v1",
  testnet: process.env.PLEXA_LZ_SCAN_TESTNET_URL ?? "https://scan-testnet.layerzero-api.com/v1",
};

const SCAN_WEB: Record<LzNetwork, string> = {
  mainnet: "https://layerzeroscan.com",
  testnet: "https://testnet.layerzeroscan.com",
};

export interface LzDeployment {
  version: number;
  eid: string;
  stage?: string;
  chainKey?: string;
  endpointV2?: { address: string };
  endpointV2View?: { address: string };
  sendUln302?: { address: string };
  receiveUln302?: { address: string };
  executor?: { address: string };
}

export interface LzChainEntry {
  chainKey: string;
  chainDetails?: {
    nativeChainId?: number;
    name?: string;
    shortName?: string;
    chainType?: string;
    chainLayer?: string;
    chainStatus?: string;
    nativeCurrency?: { symbol?: string; decimals?: number };
    averageBlockTime?: number;
  };
  deployments?: LzDeployment[];
  dvns?: Record<string, { canonicalName?: string; id?: string; version?: number; deprecated?: boolean }>;
  blockExplorers?: { url: string }[];
}

export type LzMetadata = Record<string, LzChainEntry>;

let metadataCache: { fetchedAt: number; data: Promise<LzMetadata> } | undefined;

export function getMetadata(fetchImpl: typeof fetch = fetch): Promise<LzMetadata> {
  const now = Date.now();
  if (!metadataCache || now - metadataCache.fetchedAt > METADATA_TTL_MS) {
    const data = fetchImpl(METADATA_URL, { signal: AbortSignal.timeout(30_000) }).then(async (res) => {
      if (!res.ok) throw new Error(`LayerZero metadata API returned HTTP ${res.status}`);
      return (await res.json()) as LzMetadata;
    });
    metadataCache = { fetchedAt: now, data };
    data.catch(() => {
      metadataCache = undefined;
    });
  }
  return metadataCache.data;
}

export interface LzChainMatch {
  metadataKey: string;
  entry: LzChainEntry;
}

/**
 * Finds chains in the metadata by metadata key, chain key, native chain ID or endpoint ID.
 * Falls back to a substring search over keys and names.
 */
export function findChains(metadata: LzMetadata, query: string): { exact?: LzChainMatch; matches: LzChainMatch[] } {
  const q = query.trim().toLowerCase();
  const entries = Object.entries(metadata)
    .filter((e): e is [string, LzChainEntry] => typeof e[1] === "object" && e[1] !== null)
    .map(([metadataKey, entry]) => ({ metadataKey, entry }));

  const exact =
    entries.find((m) => m.metadataKey.toLowerCase() === q || m.entry.chainKey?.toLowerCase() === q) ??
    (/^\d+$/.test(q)
      ? (entries.find((m) => (m.entry.deployments ?? []).some((d) => d.eid === q)) ??
        entries.find((m) => String(m.entry.chainDetails?.nativeChainId) === q))
      : undefined);
  if (exact) return { exact, matches: [exact] };

  const matches = entries.filter(
    (m) =>
      m.metadataKey.toLowerCase().includes(q) ||
      m.entry.chainKey?.toLowerCase().includes(q) ||
      m.entry.chainDetails?.name?.toLowerCase().includes(q),
  );
  return { matches };
}

export function summarizeChain({ metadataKey, entry }: LzChainMatch) {
  const d = entry.chainDetails ?? {};
  const v2 = (entry.deployments ?? []).filter((x) => x.version === 2);
  const dvnNames = new Set<string>();
  for (const dvn of Object.values(entry.dvns ?? {})) {
    if (!dvn.deprecated && dvn.canonicalName) dvnNames.add(dvn.canonicalName);
  }
  return {
    metadataKey,
    chainKey: entry.chainKey,
    name: d.name ?? d.shortName,
    chainId: d.nativeChainId ?? null,
    chainType: d.chainType,
    layer: d.chainLayer,
    status: d.chainStatus,
    nativeToken: d.nativeCurrency?.symbol,
    averageBlockTimeMs: d.averageBlockTime,
    explorers: (entry.blockExplorers ?? []).map((e) => e.url),
    layerZeroV2: v2.map((x) => ({
      eid: Number(x.eid),
      stage: x.stage,
      endpointV2: x.endpointV2?.address,
      sendUln302: x.sendUln302?.address,
      receiveUln302: x.receiveUln302?.address,
      executor: x.executor?.address,
    })),
    otherEids: (entry.deployments ?? []).filter((x) => x.version !== 2).map((x) => Number(x.eid)),
    activeDvns: [...dvnNames].sort(),
  };
}

// ---------------------------------------------------------------- Scan API

export interface ScanMessage {
  pathway: {
    srcEid: number;
    dstEid: number;
    sender: { address: string; id?: string; name?: string; chain?: string };
    receiver: { address: string; id?: string; name?: string; chain?: string };
    nonce?: number;
  };
  source?: { status?: string; tx?: { txHash?: string; blockTimestamp?: number; from?: string } };
  destination?: {
    status?: string;
    tx?: { txHash?: string; blockTimestamp?: number };
    lzCompose?: { status?: string };
    nativeDrop?: { status?: string };
  };
  verification?: {
    dvn?: { status?: string; dvns?: Record<string, { status?: string; optional?: boolean }> };
    sealer?: { status?: string };
  };
  config?: {
    error?: boolean;
    inboundConfig?: {
      confirmations?: number;
      requiredDVNs?: string[];
      requiredDVNNames?: string[];
      optionalDVNs?: string[];
      optionalDVNNames?: string[];
      optionalDVNThreshold?: number;
    };
  };
  guid?: string;
  status?: { name?: string; message?: string };
  created?: string;
  updated?: string;
}

export async function scanGet(
  network: LzNetwork,
  path: string,
  fetchImpl: typeof fetch = fetch,
): Promise<{ data: ScanMessage[]; nextToken?: string }> {
  const res = await fetchImpl(`${SCAN_API[network]}${path}`, { signal: AbortSignal.timeout(20_000) });
  if (res.status === 404) return { data: [] };
  if (!res.ok) throw new Error(`LayerZero Scan API returned HTTP ${res.status}`);
  return (await res.json()) as { data: ScanMessage[]; nextToken?: string };
}

/** Plain-language hints for LayerZero Scan message statuses. */
export const STATUS_HELP: Record<string, string> = {
  INFLIGHT:
    "The source transaction is confirmed and the message is on its way. DVNs are verifying it; delivery normally follows within minutes.",
  CONFIRMING: "Waiting for enough block confirmations on the source chain before the message can be verified.",
  DELIVERED: "The message was verified and executed on the destination chain. Nothing else to do.",
  FAILED:
    "Delivery failed. The message did not execute on the destination chain; check the destination app and retry if possible.",
  PAYLOAD_STORED:
    "The message was verified but execution on the destination reverted, so the payload is stored on-chain. It can be retried (lzReceive) once the cause is fixed, for example with more gas.",
  BLOCKED:
    "An earlier message on the same pathway has not been delivered yet. This app uses ordered delivery, so this message waits behind it.",
  APPLICATION_BURNED: "The receiving application burned (permanently cancelled) this message. It will not be delivered.",
  APPLICATION_SKIPPED: "The receiving application skipped this message. It will not be delivered.",
  UNRESOLVABLE_COMMAND: "This lzRead request could not be resolved by the DVNs.",
  MALFORMED_COMMAND: "This lzRead request was malformed and cannot be processed.",
};

function iso(ts?: number): string | undefined {
  return ts ? new Date(ts * 1000).toISOString() : undefined;
}

/** Turns a raw Scan message into a compact, explainable summary. */
export function summarizeMessage(m: ScanMessage, network: LzNetwork) {
  const statusName = m.status?.name ?? "UNKNOWN";
  const inbound = m.config?.inboundConfig;
  const names = new Map<string, string>();
  (inbound?.requiredDVNs ?? []).forEach((a, i) => names.set(a.toLowerCase(), inbound?.requiredDVNNames?.[i] ?? a));
  (inbound?.optionalDVNs ?? []).forEach((a, i) => names.set(a.toLowerCase(), inbound?.optionalDVNNames?.[i] ?? a));

  const dvns = Object.entries(m.verification?.dvn?.dvns ?? {}).map(([addr, v]) => ({
    name: names.get(addr.toLowerCase()) ?? "Unknown DVN",
    address: addr,
    status: v.status,
    optional: v.optional ?? false,
  }));
  const pendingDvns = dvns.filter((d) => d.status !== "SUCCEEDED" && !d.optional).map((d) => d.name);

  const sentAt = m.source?.tx?.blockTimestamp;
  const deliveredAt = m.destination?.tx?.blockTimestamp;
  const srcTx = m.source?.tx?.txHash;

  return {
    guid: m.guid,
    status: statusName,
    statusDetail: m.status?.message,
    meaning: STATUS_HELP[statusName],
    from: {
      chain: m.pathway.sender.chain,
      eid: m.pathway.srcEid,
      app: m.pathway.sender.name ?? m.pathway.sender.id,
      oapp: m.pathway.sender.address,
      wallet: m.source?.tx?.from,
      txHash: srcTx,
      sentAt: iso(sentAt),
    },
    to: {
      chain: m.pathway.receiver.chain,
      eid: m.pathway.dstEid,
      app: m.pathway.receiver.name ?? m.pathway.receiver.id,
      oapp: m.pathway.receiver.address,
      txHash: m.destination?.tx?.txHash,
      deliveredAt: iso(deliveredAt),
    },
    deliverySeconds: sentAt && deliveredAt ? deliveredAt - sentAt : undefined,
    verification: {
      status: m.verification?.dvn?.status,
      requiredConfirmations: inbound?.confirmations,
      dvns,
      waitingOn: pendingDvns.length > 0 && statusName !== "DELIVERED" ? pendingDvns : undefined,
    },
    compose: m.destination?.lzCompose?.status !== "N/A" ? m.destination?.lzCompose?.status : undefined,
    nonce: m.pathway.nonce,
    scanUrl: srcTx ? `${SCAN_WEB[network]}/tx/${srcTx}` : undefined,
  };
}
