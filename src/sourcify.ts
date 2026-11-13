import type { Abi } from "viem";

const SOURCIFY_URL = process.env.PLEXA_SOURCIFY_URL ?? "https://sourcify.dev/server";

export interface VerifiedContract {
  match: "match" | "exact_match";
  name?: string;
  compilerVersion?: string;
  language?: string;
  verifiedAt?: string;
  abi: Abi;
  isProxy: boolean;
  proxyType?: string | null;
  implementations: { address: string; name?: string }[];
  sources?: Record<string, { content: string }>;
}

interface SourcifyResponse {
  match: "match" | "exact_match" | null;
  verifiedAt?: string;
  abi?: Abi;
  compilation?: { name?: string; compilerVersion?: string; language?: string };
  proxyResolution?: {
    isProxy?: boolean;
    proxyType?: string | null;
    implementations?: { address: string; name?: string }[];
  };
  sources?: Record<string, { content: string }>;
}

const cache = new Map<string, Promise<VerifiedContract | null>>();

/** Fetches verification data from Sourcify. Returns null when the contract is not verified there. */
export function getVerifiedContract(
  chainId: number,
  address: string,
  opts: { withSources?: boolean } = {},
): Promise<VerifiedContract | null> {
  const key = `${chainId}:${address.toLowerCase()}:${opts.withSources ? "src" : "abi"}`;
  let pending = cache.get(key);
  if (!pending) {
    pending = fetchVerified(chainId, address, opts.withSources ?? false);
    cache.set(key, pending);
    pending.catch(() => cache.delete(key));
  }
  return pending;
}

async function fetchVerified(chainId: number, address: string, withSources: boolean): Promise<VerifiedContract | null> {
  const fields = ["abi", "compilation", "proxyResolution", ...(withSources ? ["sources"] : [])].join(",");
  const url = `${SOURCIFY_URL}/v2/contract/${chainId}/${address}?fields=${fields}`;
  const res = await fetch(url, { signal: AbortSignal.timeout(20_000) });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Sourcify returned HTTP ${res.status}`);
  const body = (await res.json()) as SourcifyResponse;
  if (!body.match) return null;
  return {
    match: body.match,
    name: body.compilation?.name,
    compilerVersion: body.compilation?.compilerVersion,
    language: body.compilation?.language,
    verifiedAt: body.verifiedAt,
    abi: body.abi ?? [],
    isProxy: body.proxyResolution?.isProxy ?? false,
    proxyType: body.proxyResolution?.proxyType,
    implementations: body.proxyResolution?.implementations ?? [],
    sources: body.sources,
  };
}
