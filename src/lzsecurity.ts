/**
 * Reads a LayerZero V2 app's security configuration from the chain and explains it.
 * Everything here is a view call; nothing is signed or sent.
 */
import { decodeAbiParameters, getAddress, parseAbi, type Address, type Hex, type PublicClient } from "viem";
import { explorerAddressUrl, type ChainConfig, type ChainRegistry } from "./chains.js";
import { findChains, getMetadata, type LzChainEntry, type LzDeployment, type LzMetadata } from "./layerzero.js";

const ENDPOINT_ABI = parseAbi([
  "function getSendLibrary(address sender, uint32 dstEid) view returns (address)",
  "function getReceiveLibrary(address receiver, uint32 srcEid) view returns (address lib, bool isDefault)",
  "function getConfig(address oapp, address lib, uint32 eid, uint32 configType) view returns (bytes)",
  "function delegates(address oapp) view returns (address)",
]);

const OAPP_ABI = parseAbi([
  "function peers(uint32 eid) view returns (bytes32)",
  "function owner() view returns (address)",
  "function endpoint() view returns (address)",
  "function token() view returns (address)",
  "function oftVersion() view returns (bytes4 interfaceId, uint64 version)",
  "function symbol() view returns (string)",
  "function name() view returns (string)",
]);

const ULN_ABI = parseAbi([
  "function getAppUlnConfig(address oapp, uint32 remoteEid) view returns ((uint64 confirmations, uint8 requiredDVNCount, uint8 optionalDVNCount, uint8 optionalDVNThreshold, address[] requiredDVNs, address[] optionalDVNs))",
]);

const SAFE_ABI = parseAbi(["function getThreshold() view returns (uint256)", "function getOwners() view returns (address[])"]);

const ULN_CONFIG = [
  {
    type: "tuple",
    components: [
      { name: "confirmations", type: "uint64" },
      { name: "requiredDVNCount", type: "uint8" },
      { name: "optionalDVNCount", type: "uint8" },
      { name: "optionalDVNThreshold", type: "uint8" },
      { name: "requiredDVNs", type: "address[]" },
      { name: "optionalDVNs", type: "address[]" },
    ],
  },
] as const;

const EXECUTOR_CONFIG = [
  {
    type: "tuple",
    components: [
      { name: "maxMessageSize", type: "uint32" },
      { name: "executor", type: "address" },
    ],
  },
] as const;

const CONFIG_TYPE_EXECUTOR = 1;
const CONFIG_TYPE_ULN = 2;
const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";

export interface UlnConfig {
  confirmations: bigint;
  requiredDVNCount: number;
  optionalDVNCount: number;
  optionalDVNThreshold: number;
  requiredDVNs: readonly Address[];
  optionalDVNs: readonly Address[];
}

export type Severity = "high" | "medium" | "info";

export interface Finding {
  severity: Severity;
  message: string;
}

export interface DvnInfo {
  name: string;
  deprecated?: boolean;
  dead?: boolean;
}

export type DvnDirectory = Map<string, DvnInfo>;

export function decodeUlnConfig(data: Hex): UlnConfig {
  const [c] = decodeAbiParameters(ULN_CONFIG, data);
  return c;
}

export function decodeExecutorConfig(data: Hex): { maxMessageSize: number; executor: Address } {
  const [c] = decodeAbiParameters(EXECUTOR_CONFIG, data);
  return c;
}

/** Builds an address → DVN name map from one chain's LayerZero metadata entry. */
export function dvnDirectory(entry: LzChainEntry | undefined, deadDvn?: string): DvnDirectory {
  const dir: DvnDirectory = new Map();
  for (const [addr, info] of Object.entries(entry?.dvns ?? {})) {
    const dead = info.id === "lz-dead-dvn";
    dir.set(addr.toLowerCase(), { name: dead ? "Dead DVN (blocks the pathway)" : (info.canonicalName ?? info.id ?? "unknown"), deprecated: info.deprecated, dead });
  }
  if (deadDvn) dir.set(deadDvn.toLowerCase(), { name: "Dead DVN (blocks the pathway)", dead: true });
  return dir;
}

export function dvnName(dir: DvnDirectory, address: string): string {
  const info = dir.get(address.toLowerCase());
  if (!info) return `unlisted DVN ${address.slice(0, 6)}…${address.slice(-4)}`;
  return info.deprecated ? `${info.name} (deprecated)` : info.name;
}

/** Number of independent DVN signatures a message needs on this pathway. */
export function verifiersNeeded(c: UlnConfig): number {
  return c.requiredDVNCount + c.optionalDVNThreshold;
}

export function isDeadPathway(c: UlnConfig, dir: DvnDirectory): boolean {
  return [...c.requiredDVNs, ...c.optionalDVNs].some((a) => dir.get(a.toLowerCase())?.dead);
}

/** Plain-language view of one direction (send or receive) of a pathway, plus what is worth flagging. */
export function describeUln(c: UlnConfig, dir: DvnDirectory, direction: "send" | "receive", customised: boolean | undefined) {
  const findings: Finding[] = [];
  const needed = verifiersNeeded(c);
  const dead = isDeadPathway(c, dir);
  const label = direction === "send" ? "Outgoing messages" : "Incoming messages";
  if (dead) {
    findings.push({ severity: "info", message: `${label} are blocked by a dead DVN, so this direction is closed.` });
  } else if (needed === 0) {
    findings.push({ severity: "high", message: `${label} need no DVN verification at all.` });
  } else if (needed === 1) {
    const only = c.requiredDVNCount === 1 ? dvnName(dir, c.requiredDVNs[0]!) : "a single optional DVN";
    findings.push({ severity: "high", message: `${label} can be approved by one DVN alone (${only}). That DVN is a single point of failure.` });
  }
  if (customised === false && !dead) {
    findings.push({ severity: "info", message: `${label} use LayerZero's default DVN settings, which can change without the app's involvement.` });
  }
  const optional =
    c.optionalDVNCount > 0 ? `, plus ${c.optionalDVNThreshold} of ${c.optionalDVNCount} optional` : "";
  return {
    summary: dead ? "closed" : `${needed} DVN signature${needed === 1 ? "" : "s"} needed (${c.requiredDVNCount} required${optional})`,
    requiredDVNs: c.requiredDVNs.map((a) => dvnName(dir, a)),
    optionalDVNs: c.optionalDVNs.map((a) => dvnName(dir, a)),
    optionalThreshold: c.optionalDVNThreshold,
    blockConfirmations: Number(c.confirmations),
    settings: customised === undefined ? "unknown" : customised ? "set by the app" : "LayerZero defaults",
    findings,
  };
}

export type ControllerKind = "multisig" | "contract" | "single key" | "none";

export function describeController(code: Hex | undefined, safe?: { threshold: bigint; owners: number }) {
  const isEoa = !code || code === "0x" || code.toLowerCase().startsWith("0xef0100");
  if (safe) return { kind: "multisig" as ControllerKind, detail: `Safe multisig, ${safe.threshold} of ${safe.owners} signers` };
  if (isEoa) return { kind: "single key" as ControllerKind, detail: "a regular wallet (one private key)" };
  return { kind: "contract" as ControllerKind, detail: "a smart contract (for example a timelock or governance contract)" };
}

export function overallRisk(findings: Finding[]): "high" | "medium" | "low" {
  if (findings.some((f) => f.severity === "high")) return "high";
  if (findings.some((f) => f.severity === "medium")) return "medium";
  return "low";
}

interface LocalLz {
  eid: number;
  stage: string;
  endpoint: Address;
  deployment: LzDeployment & { deadDVN?: { address: string }; blockedMessageLib?: { address: string } };
  entry: LzChainEntry;
}

/** Finds the LayerZero V2 deployment for a Plexa chain in the metadata. */
export function findLocalDeployment(metadata: LzMetadata, chain: ChainConfig): LocalLz | undefined {
  const stage = chain.testnet ? "testnet" : "mainnet";
  const candidates: LzChainEntry[] = [];
  if (chain.lzChainKey) {
    const { exact, matches } = findChains(metadata, chain.lzChainKey);
    if (exact) candidates.push(exact.entry);
    else candidates.push(...matches.map((m) => m.entry));
  }
  if (chain.chainId !== undefined) {
    for (const e of Object.values(metadata)) if (e.chainDetails?.nativeChainId === chain.chainId) candidates.push(e);
  }
  for (const entry of candidates) {
    for (const d of entry.deployments ?? []) {
      if (d.version !== 2 || !d.endpointV2?.address) continue;
      if (chain.lzEid !== undefined ? Number(d.eid) === chain.lzEid : d.stage === stage) {
        return { eid: Number(d.eid), stage: d.stage ?? stage, endpoint: getAddress(d.endpointV2.address), deployment: d, entry };
      }
    }
  }
  return undefined;
}

/** All V2 endpoint IDs of one stage, with a readable chain name. */
export function remoteEids(metadata: LzMetadata, stage: string, exclude: number): Map<number, string> {
  const out = new Map<number, string>();
  for (const [key, e] of Object.entries(metadata)) {
    for (const d of e.deployments ?? []) {
      if (d.version !== 2 || d.stage !== stage) continue;
      const eid = Number(d.eid);
      if (eid !== exclude && !out.has(eid)) out.set(eid, e.chainDetails?.name ?? e.chainKey ?? key);
    }
  }
  return out;
}

type Res = { ok: true; value: unknown } | { ok: false };

async function many(client: PublicClient, contracts: readonly unknown[]): Promise<Res[]> {
  if (contracts.length === 0) return [];
  const res = (await client.multicall({ contracts: contracts as never, allowFailure: true, batchSize: 0 })) as unknown as {
    status: "success" | "failure";
    result?: unknown;
  }[];
  return res.map((r) => (r.status === "success" ? { ok: true as const, value: r.result } : { ok: false as const }));
}

function val<T>(r: Res | undefined): T | undefined {
  return r && r.ok ? (r.value as T) : undefined;
}

export interface SecurityOptions {
  remotes?: string[];
  maxPathways?: number;
}

export async function checkAppSecurity(registry: ChainRegistry, chainKey: string, rawAddress: string, opts: SecurityOptions = {}) {
  const chain = registry.get(chainKey);
  const client = await registry.client(chain.key);
  const app = getAddress(rawAddress);
  const metadata = await getMetadata();
  const local = findLocalDeployment(metadata, chain);
  if (!local) throw new Error(`LayerZero has not published a V2 endpoint for ${chain.name} yet.`);

  let remotes = remoteEids(metadata, local.stage, local.eid);
  if (opts.remotes?.length) {
    const wanted = new Map<number, string>();
    for (const q of opts.remotes) {
      const eid = resolveRemote(registry, metadata, q, local.stage);
      if (eid === undefined) throw new Error(`Unknown remote chain "${q}". Use a Plexa chain key, a LayerZero chain key or an endpoint ID.`);
      wanted.set(eid, remotes.get(eid) ?? `EID ${eid}`);
    }
    remotes = wanted;
  }
  const eids = [...remotes.keys()];

  const code = await client.getCode({ address: app });
  if (!code || code === "0x") {
    return { found: false, message: `${app} has no contract code on ${chain.name}, so it is not a LayerZero app there.` };
  }

  const basics = await many(client, [
    { address: app, abi: OAPP_ABI, functionName: "endpoint" },
    { address: app, abi: OAPP_ABI, functionName: "owner" },
    { address: app, abi: OAPP_ABI, functionName: "oftVersion" },
    { address: app, abi: OAPP_ABI, functionName: "token" },
    { address: app, abi: OAPP_ABI, functionName: "symbol" },
    { address: app, abi: OAPP_ABI, functionName: "name" },
    { address: local.endpoint, abi: ENDPOINT_ABI, functionName: "delegates", args: [app] },
    ...eids.map((eid) => ({ address: app, abi: OAPP_ABI, functionName: "peers", args: [eid] })),
  ]);
  const [endpointR, ownerR, oftR, tokenR, symbolR, nameR, delegateR, ...peerR] = basics;
  const peers = eids
    .map((eid, i) => ({ eid, name: remotes.get(eid)!, peer: peerR[i]?.ok ? (peerR[i].value as Hex) : undefined }))
    .filter((p): p is { eid: number; name: string; peer: Hex } => Boolean(p.peer) && !/^0x0*$/.test(p.peer!));

  const endpointAddr = endpointR?.ok ? (endpointR.value as Address) : undefined;
  if (peers.length === 0 && !endpointAddr) {
    return {
      found: false,
      message: `${app} on ${chain.name} does not look like a LayerZero V2 app (no endpoint() and no peers). For an OFT that wraps a token, pass the OFT or adapter address, not the token.`,
    };
  }

  const max = opts.maxPathways ?? 12;
  const checked = peers.slice(0, max);
  const libs = await many(client, checked.flatMap((p) => [
    { address: local.endpoint, abi: ENDPOINT_ABI, functionName: "getSendLibrary", args: [app, p.eid] },
    { address: local.endpoint, abi: ENDPOINT_ABI, functionName: "getReceiveLibrary", args: [app, p.eid] },
  ]));
  const libPairs = checked.map((_, i) => ({
    send: val<Address>(libs[i * 2]),
    receive: val<[Address, boolean]>(libs[i * 2 + 1])?.[0],
  }));

  const blocked = local.deployment.blockedMessageLib?.address?.toLowerCase();
  const cfgCalls: unknown[] = [];
  checked.forEach((p, i) => {
    const { send, receive } = libPairs[i]!;
    const s = send ?? ZERO_ADDRESS;
    const r = receive ?? ZERO_ADDRESS;
    cfgCalls.push(
      { address: local.endpoint, abi: ENDPOINT_ABI, functionName: "getConfig", args: [app, s, p.eid, CONFIG_TYPE_ULN] },
      { address: local.endpoint, abi: ENDPOINT_ABI, functionName: "getConfig", args: [app, r, p.eid, CONFIG_TYPE_ULN] },
      { address: local.endpoint, abi: ENDPOINT_ABI, functionName: "getConfig", args: [app, s, p.eid, CONFIG_TYPE_EXECUTOR] },
      { address: s, abi: ULN_ABI, functionName: "getAppUlnConfig", args: [app, p.eid] },
      { address: r, abi: ULN_ABI, functionName: "getAppUlnConfig", args: [app, p.eid] },
    );
  });
  const cfg = await many(client, cfgCalls);

  const dir = dvnDirectory(local.entry, local.deployment.deadDVN?.address);
  const executors = new Map<string, string>();
  for (const k of ["executor", "lzExecutor"] as const) {
    const a = (local.deployment as unknown as Record<string, { address?: string } | undefined>)[k]?.address;
    if (a) executors.set(a.toLowerCase(), "LayerZero executor");
  }

  const allFindings: Finding[] = [];
  const pathways = checked.map((p, i) => {
    const at = (k: number) => cfg[i * 5 + k];
    const { send, receive } = libPairs[i]!;
    const isCustom = (r: { ok: boolean; value?: unknown } | undefined) => {
      if (!r?.ok) return undefined;
      const c = r.value as UlnConfig;
      return c.confirmations !== 0n || c.requiredDVNCount !== 0 || c.optionalDVNCount !== 0;
    };
    const dirOut = (lib: Address | undefined, r: { ok: boolean; value?: unknown } | undefined, d: "send" | "receive", custom: boolean | undefined) => {
      if (lib && blocked && lib.toLowerCase() === blocked) {
        return { summary: "closed", findings: [{ severity: "info" as Severity, message: `${d === "send" ? "Outgoing" : "Incoming"} messages use LayerZero's blocked library, so this direction is closed.` }] };
      }
      if (!r?.ok) return { summary: "could not be read", findings: [] as Finding[] };
      return describeUln(decodeUlnConfig(r.value as Hex), dir, d, custom);
    };
    const sendOut = dirOut(send, at(0), "send", isCustom(at(3)));
    const recvOut = dirOut(receive, at(1), "receive", isCustom(at(4)));
    let executor: string | undefined;
    const ex = at(2);
    if (ex?.ok) {
      const e = decodeExecutorConfig(ex.value as Hex).executor;
      executor = executors.get(e.toLowerCase()) ?? e;
    }
    const findings = [...sendOut.findings, ...recvOut.findings];
    allFindings.push(...findings.map((f) => ({ ...f, message: `${p.name}: ${f.message}` })));
    const { findings: _s, ...sendRest } = sendOut;
    const { findings: _r, ...recvRest } = recvOut;
    return {
      remote: `${p.name} (EID ${p.eid})`,
      peer: peerToAddress(p.peer),
      outgoing: sendRest,
      incoming: recvRest,
      executor,
      flags: findings.map((f) => `${f.severity}: ${f.message}`),
    };
  });

  const controllers = await describeControllers(client, [
    ["owner", ownerR?.ok ? (ownerR.value as Address) : undefined],
    ["delegate", delegateR?.ok ? (delegateR.value as Address) : undefined],
  ]);
  for (const c of controllers) {
    if (c.kind === "single key") {
      allFindings.push({
        severity: "medium",
        message:
          c.role === "delegate"
            ? "The endpoint delegate, which can change the DVN and library settings, is a single private key."
            : "The owner, which can change peers and settings, is a single private key.",
      });
    }
    if (c.kind === "multisig" && /, 1 of /.test(c.detail)) {
      allFindings.push({ severity: "medium", message: `The ${c.role} is a multisig that needs only one signature.` });
    }
  }

  // the most common DVN set across checked pathways, so a reader gets the picture in one line
  const setups = new Map<string, number>();
  for (const p of pathways) {
    for (const raw of [p.outgoing, p.incoming]) {
      const d = raw as { summary: string; requiredDVNs?: string[]; optionalDVNs?: string[]; optionalThreshold?: number };
      if (!d.requiredDVNs || !d.optionalDVNs) continue;
      const names = [...d.requiredDVNs, ...(d.optionalDVNs.length ? [`${d.optionalThreshold} of ${d.optionalDVNs.join(", ")}`] : [])];
      const k = `${d.summary.replace(/ \(.*\)$/, "")}: ${names.join(", ")}`;
      setups.set(k, (setups.get(k) ?? 0) + 1);
    }
  }
  const typical = [...setups.entries()].sort((a, b) => b[1] - a[1])[0];
  const directions = pathways.length * 2;

  const oft = oftR?.ok ? (oftR.value as [Hex, bigint]) : undefined;
  const token = tokenR?.ok ? (tokenR.value as Address) : undefined;
  const risk = overallRisk(allFindings);
  return {
    found: true,
    app: {
      chain: chain.name,
      address: app,
      kind: oft ? (token && token.toLowerCase() !== app.toLowerCase() ? "OFT adapter (wraps an existing token)" : "OFT (omnichain token)") : "OApp",
      name: nameR?.ok ? nameR.value : undefined,
      symbol: symbolR?.ok ? symbolR.value : undefined,
      token: token && token.toLowerCase() !== app.toLowerCase() ? token : undefined,
      explorer: explorerAddressUrl(chain, app),
    },
    control: controllers.map(({ role, address, kind, detail }) => ({ role, address, kind, detail })),
    pathways,
    summary: {
      risk,
      typicalSetup: typical ? `${typical[0]} (${typical[1]} of ${directions} directions checked)` : undefined,
      connectedChains: peers.length,
      pathwaysChecked: checked.length,
      truncated: peers.length > checked.length ? `Checked the first ${checked.length} of ${peers.length} connected chains. Pass remotes or a higher maxPathways to see others.` : undefined,
      findings: allFindings.filter((f) => f.severity !== "info").map((f) => f.message),
      notes: dedupe(allFindings.filter((f) => f.severity === "info").map((f) => f.message.replace(/^[^:]+: /, ""))),
    },
    disclaimer: "Automated read of on-chain configuration at this moment. It is not an audit and does not cover the app's own code.",
  };
}

function dedupe(list: string[]): string[] {
  return [...new Set(list)];
}

function peerToAddress(peer: Hex): string {
  const body = peer.slice(2);
  return body.slice(0, 24) === "0".repeat(24) ? getAddress(`0x${body.slice(24)}`) : peer;
}

function resolveRemote(registry: ChainRegistry, metadata: LzMetadata, q: string, stage: string): number | undefined {
  const n = Number(q);
  if (Number.isInteger(n) && n > 30000) return n;
  try {
    const c = registry.get(q);
    if (c.lzEid) return c.lzEid;
    if (c.lzChainKey) q = c.lzChainKey;
  } catch {
    // not a Plexa chain key
  }
  const { exact, matches } = findChains(metadata, q);
  for (const m of exact ? [exact] : matches) {
    const d = (m.entry.deployments ?? []).find((x) => x.version === 2 && x.stage === stage);
    if (d) return Number(d.eid);
  }
  return undefined;
}

async function describeControllers(client: PublicClient, list: [string, Address | undefined][]) {
  const present = list.filter((x): x is [string, Address] => Boolean(x[1]) && x[1] !== ZERO_ADDRESS);
  const codes = await Promise.all(present.map(([, a]) => client.getCode({ address: a }).catch(() => undefined)));
  const safes = await many(client, present.flatMap(([, a]) => [
    { address: a, abi: SAFE_ABI, functionName: "getThreshold" },
    { address: a, abi: SAFE_ABI, functionName: "getOwners" },
  ]));
  const out = present.map(([role, address], i) => {
    const t = safes[i * 2];
    const o = safes[i * 2 + 1];
    const safe = t?.ok && o?.ok ? { threshold: t.value as bigint, owners: (o.value as Address[]).length } : undefined;
    return { role, address, ...describeController(codes[i], safe) };
  });
  for (const [role, address] of list) {
    if (address === ZERO_ADDRESS) out.push({ role, address, kind: "none", detail: "renounced (no one)" });
  }
  return out;
}
