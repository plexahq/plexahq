import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { getAddress } from "viem";
import { z } from "zod";
import type { ChainRegistry } from "../chains.js";
import { compactMessage, findChains, getMetadata, scanGet, summarizeChain, summarizeMessage, type LzNetwork } from "../layerzero.js";
import { checkAppSecurity } from "../lzsecurity.js";
import { safe } from "../result.js";

const READ_ONLY = { readOnlyHint: true, destructiveHint: false, openWorldHint: true } as const;

const network = z
  .enum(["mainnet", "testnet"])
  .optional()
  .describe('LayerZero network to query. Defaults to "mainnet".');

export function registerLayerZeroTools(server: McpServer, registry: ChainRegistry): void {
  server.registerTool(
    "lz_chain_info",
    {
      title: "LayerZero chain info",
      description:
        "Looks up a chain in LayerZero's official deployment registry: endpoint ID (EID), EndpointV2 / message library / executor addresses, active DVNs and explorers. Accepts a Plexa chain key, a LayerZero chain key, a chain ID, an EID or a name fragment such as \"zero\".",
      inputSchema: {
        query: z.string().min(1).describe('e.g. "base", "zero", "30184" or "8453"'),
      },
      annotations: READ_ONLY,
    },
    safe(async ({ query }) => {
      const metadata = await getMetadata();
      let q = query;
      try {
        const local = registry.get(query);
        if (local.lzChainKey) q = local.lzChainKey;
      } catch {
        // not a Plexa chain key; search the registry directly
      }
      const { exact, matches } = findChains(metadata, q);
      if (exact) return summarizeChain(exact);
      if (matches.length === 0) return { found: false, message: `No LayerZero chain matches "${query}".` };
      if (matches.length === 1) return summarizeChain(matches[0]!);
      return {
        found: matches.length,
        message: "Several chains match; call again with one of these keys for full details.",
        matches: matches.slice(0, 25).map((m) => ({
          key: m.metadataKey,
          name: m.entry.chainDetails?.name,
          chainId: m.entry.chainDetails?.nativeChainId ?? null,
          eids: (m.entry.deployments ?? []).map((d) => Number(d.eid)),
        })),
      };
    }),
  );

  server.registerTool(
    "lz_track_message",
    {
      title: "Track LayerZero message",
      description:
        "Tracks the cross-chain LayerZero message(s) created by a source-chain transaction: where it is, which DVNs have verified it, whether it was delivered and, if stuck, what that means in plain language.",
      inputSchema: {
        txHash: z
          .string()
          .regex(/^0x[0-9a-fA-F]{64}$/)
          .describe("Hash of the source-chain transaction that sent the message"),
        network,
      },
      annotations: READ_ONLY,
    },
    safe(async ({ txHash, network: net }) => {
      const n: LzNetwork = net ?? "mainnet";
      const { data } = await scanGet(n, `/messages/tx/${txHash}`);
      if (data.length === 0) {
        return {
          found: false,
          message:
            n === "mainnet"
              ? "No LayerZero message found for this transaction. It may not be a LayerZero transaction, may be on testnet (try network=testnet), or may not be indexed yet (wait a minute and retry)."
              : "No LayerZero testnet message found for this transaction.",
        };
      }
      return { found: true, messages: data.map((m) => summarizeMessage(m, n)) };
    }),
  );

  server.registerTool(
    "lz_latest_messages",
    {
      title: "Latest LayerZero messages",
      description:
        "Shows the most recent cross-chain messages across the whole LayerZero network: which apps are sending, between which chains, and whether they were delivered. Useful for 'what is happening on LayerZero right now?'.",
      inputSchema: {
        limit: z.number().int().min(1).max(50).optional().describe("Max messages to return (default 10)"),
        network,
      },
      annotations: READ_ONLY,
    },
    safe(async ({ limit, network: net }) => {
      const n: LzNetwork = net ?? "mainnet";
      const max = limit ?? 10;
      const { data } = await scanGet(n, `/messages/latest?limit=${max}`);
      return { count: data.length, messages: data.slice(0, max).map((m) => compactMessage(m, n)) };
    }),
  );

  server.registerTool(
    "lz_list_messages",
    {
      title: "List LayerZero messages",
      description:
        "Lists recent LayerZero cross-chain messages sent by a wallet, or handled by an OApp (when oappEid is given), newest first.",
      inputSchema: {
        address: z.string().regex(/^0x[0-9a-fA-F]{40}$/).describe("Wallet address, or OApp contract address"),
        oappEid: z
          .number()
          .int()
          .positive()
          .optional()
          .describe("If set, treat address as an OApp on this LayerZero endpoint ID"),
        limit: z.number().int().min(1).max(50).optional().describe("Max messages to return (default 10)"),
        network,
      },
      annotations: READ_ONLY,
    },
    safe(async ({ address, oappEid, limit, network: net }) => {
      const n: LzNetwork = net ?? "mainnet";
      const addr = getAddress(address).toLowerCase();
      const max = limit ?? 10;
      const path = oappEid ? `/messages/oapp/${oappEid}/${addr}?limit=${max}` : `/messages/wallet/${addr}?limit=${max}`;
      const { data } = await scanGet(n, path);
      return { count: data.length, messages: data.slice(0, max).map((m) => compactMessage(m, n)) };
    }),
  );

  server.registerTool(
    "lz_app_security",
    {
      title: "LayerZero app security check",
      description:
        "Checks a LayerZero V2 app (OApp or OFT) straight from the chain: which chains it trusts, how many DVNs must verify each incoming and outgoing message and which ones, block confirmations, executor, and who can change the settings (single key, multisig or contract). Flags single points of failure, such as a pathway that one DVN can approve alone. An automated read of on-chain configuration, not an audit.",
      inputSchema: {
        chain: z.string().describe(`Chain the app is deployed on. Known chains: ${registry.keys().join(", ")}`),
        address: z.string().regex(/^0x[0-9a-fA-F]{40}$/).describe("OApp, OFT or OFT adapter contract address"),
        remotes: z
          .array(z.string())
          .max(10)
          .optional()
          .describe('Only check these remote chains (Plexa chain key, LayerZero chain key or EID), e.g. ["arbitrum", "bnb"]'),
        maxPathways: z.number().int().min(1).max(30).optional().describe("Max connected chains to check (default 12)"),
      },
      annotations: READ_ONLY,
    },
    safe(async ({ chain, address, remotes, maxPathways }) => checkAppSecurity(registry, chain, address, { remotes, maxPathways })),
  );
}
