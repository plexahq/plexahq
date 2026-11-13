import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import {
  erc20Abi,
  formatUnits,
  getAddress,
  parseEventLogs,
  parseUnits,
  type Abi,
  type AbiFunction,
  type Address,
  type Hex,
  type PublicClient,
} from "viem";
import { formatAbiItem } from "abitype";
import { z } from "zod";
import { coerceArgs, decodeCall, formatAmount, isUnlimitedApproval, parseFunction, type DecodedCall } from "../abi.js";
import { explorerAddressUrl, explorerTxUrl, type ChainConfig, type ChainRegistry } from "../chains.js";
import { errorMessage, safe } from "../result.js";
import { getVerifiedContract, type VerifiedContract } from "../sourcify.js";

const EIP1967_IMPLEMENTATION_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc";
const MAX_SOURCE_CHARS = 60_000;

const address = z
  .string()
  .regex(/^0x[0-9a-fA-F]{40}$/, "Must be a 0x-prefixed 20-byte address")
  .describe("0x-prefixed address");
const txHash = z
  .string()
  .regex(/^0x[0-9a-fA-F]{64}$/, "Must be a 0x-prefixed 32-byte transaction hash")
  .describe("Transaction hash");
const hexData = z.string().regex(/^0x([0-9a-fA-F]{2})*$/, "Must be 0x-prefixed hex");

const READ_ONLY = { readOnlyHint: true, destructiveHint: false, openWorldHint: true } as const;

export function registerEvmTools(server: McpServer, registry: ChainRegistry): void {
  const chain = z
    .string()
    .describe(`Chain key or numeric chain ID. Known chains: ${registry.keys().join(", ")}`);

  server.registerTool(
    "list_chains",
    {
      title: "List supported chains",
      description:
        "Lists every chain Plexa can talk to, including LayerZero Zero zones, with chain IDs, LayerZero endpoint IDs and whether an RPC is configured.",
      inputSchema: {},
      annotations: { ...READ_ONLY, openWorldHint: false },
    },
    safe(async () =>
      registry.list().map((c) => ({
        key: c.key,
        name: c.name,
        chainId: c.chainId ?? null,
        testnet: c.testnet,
        nativeToken: c.nativeSymbol,
        rpcConfigured: Boolean(c.rpcUrl),
        explorer: c.explorerUrl ?? null,
        layerZeroEid: c.lzEid ?? null,
        notes: c.notes,
      })),
    ),
  );

  server.registerTool(
    "get_balance",
    {
      title: "Get wallet balances",
      description:
        "Returns the native token balance of an address and, optionally, its balances of the given ERC-20 tokens.",
      inputSchema: {
        chain,
        address,
        tokens: z.array(address).max(25).optional().describe("ERC-20 token contract addresses to include"),
      },
      annotations: READ_ONLY,
    },
    safe(async ({ chain: chainKey, address: addr, tokens }) => {
      const cfg = registry.get(chainKey);
      const client = await registry.client(chainKey);
      const owner = getAddress(addr);
      const native = await client.getBalance({ address: owner });
      const tokenBalances = await Promise.all(
        (tokens ?? []).map(async (t) => {
          try {
            const token = getAddress(t);
            const meta = await tokenMeta(client, token);
            const raw = await client.readContract({ address: token, abi: erc20Abi, functionName: "balanceOf", args: [owner] });
            return { token, symbol: meta.symbol, raw, formatted: formatUnits(raw, meta.decimals) };
          } catch (error) {
            return { token: t, error: errorMessage(error) };
          }
        }),
      );
      return {
        chain: cfg.key,
        address: owner,
        native: { symbol: cfg.nativeSymbol, raw: native, formatted: formatUnits(native, cfg.nativeDecimals) },
        tokens: tokenBalances,
        explorer: explorerAddressUrl(cfg, owner),
      };
    }),
  );

  server.registerTool(
    "get_token_info",
    {
      title: "Get ERC-20 token info",
      description: "Returns name, symbol, decimals and total supply of an ERC-20 token.",
      inputSchema: { chain, token: address },
      annotations: READ_ONLY,
    },
    safe(async ({ chain: chainKey, token }) => {
      const cfg = registry.get(chainKey);
      const client = await registry.client(chainKey);
      const tokenAddress = getAddress(token);
      const [meta, name, totalSupply] = await Promise.all([
        tokenMeta(client, tokenAddress),
        client.readContract({ address: tokenAddress, abi: erc20Abi, functionName: "name" }).catch(() => undefined),
        client.readContract({ address: tokenAddress, abi: erc20Abi, functionName: "totalSupply" }),
      ]);
      return {
        chain: cfg.key,
        token: tokenAddress,
        name,
        symbol: meta.symbol,
        decimals: meta.decimals,
        totalSupply: { raw: totalSupply, formatted: formatUnits(totalSupply, meta.decimals) },
        explorer: explorerAddressUrl(cfg, tokenAddress),
      };
    }),
  );

  server.registerTool(
    "get_block",
    {
      title: "Get block",
      description: "Returns a block's number, hash, timestamp, transaction count and gas usage. Defaults to the latest block.",
      inputSchema: {
        chain,
        block: z
          .union([z.literal("latest"), z.number().int().nonnegative(), z.string().regex(/^\d+$/)])
          .optional()
          .describe('Block number, or "latest"'),
      },
      annotations: READ_ONLY,
    },
    safe(async ({ chain: chainKey, block }) => {
      const cfg = registry.get(chainKey);
      const client = await registry.client(chainKey);
      const b =
        block === undefined || block === "latest"
          ? await client.getBlock()
          : await client.getBlock({ blockNumber: BigInt(block) });
      return {
        chain: cfg.key,
        number: b.number,
        hash: b.hash,
        timestamp: new Date(Number(b.timestamp) * 1000).toISOString(),
        transactionCount: b.transactions.length,
        gasUsed: b.gasUsed,
        gasLimit: b.gasLimit,
        baseFeeGwei: b.baseFeePerGas != null ? formatUnits(b.baseFeePerGas, 9) : null,
      };
    }),
  );

  server.registerTool(
    "get_transaction",
    {
      title: "Get transaction",
      description:
        "Looks up a transaction and its receipt: status, fee, decoded function call (when the contract is verified or ERC-20) and ERC-20 transfers it caused.",
      inputSchema: { chain, hash: txHash },
      annotations: READ_ONLY,
    },
    safe(async ({ chain: chainKey, hash }) => {
      const cfg = registry.get(chainKey);
      const client = await registry.client(chainKey);
      const tx = await client.getTransaction({ hash: hash as Hex });
      const receipt = await client.getTransactionReceipt({ hash: hash as Hex }).catch(() => null);

      let decoded: DecodedCall | undefined;
      if (tx.to && tx.input && tx.input !== "0x") {
        const abi = await verifiedAbiWithImplementation(cfg, tx.to).catch(() => undefined);
        decoded = decodeCall(tx.input, abi);
      }

      const transfers = receipt
        ? await describeTransfers(client, parseEventLogs({ abi: erc20Abi, eventName: "Transfer", logs: receipt.logs }))
        : [];

      return {
        chain: cfg.key,
        hash: tx.hash,
        status: receipt ? receipt.status : "pending",
        blockNumber: tx.blockNumber,
        from: tx.from,
        to: tx.to,
        contractCreated: receipt?.contractAddress ?? undefined,
        value: { raw: tx.value, formatted: formatAmount(tx.value, cfg.nativeDecimals, cfg.nativeSymbol) },
        fee: receipt
          ? formatAmount(receipt.gasUsed * receipt.effectiveGasPrice, cfg.nativeDecimals, cfg.nativeSymbol)
          : undefined,
        gasUsed: receipt?.gasUsed,
        functionSelector: tx.input && tx.input.length >= 10 ? tx.input.slice(0, 10) : undefined,
        decodedCall: decoded,
        tokenTransfers: transfers,
        explorer: explorerTxUrl(cfg, tx.hash),
      };
    }),
  );

  server.registerTool(
    "read_contract",
    {
      title: "Read contract",
      description:
        'Calls a read-only contract function. Give the function as a Solidity signature, e.g. "function balanceOf(address owner) view returns (uint256)". Pass large integers as strings.',
      inputSchema: {
        chain,
        address,
        function: z.string().min(3).describe("Solidity function signature or JSON ABI fragment"),
        args: z.array(z.unknown()).optional().describe("Function arguments, in order"),
        blockNumber: z.union([z.number().int().nonnegative(), z.string().regex(/^\d+$/)]).optional(),
      },
      annotations: READ_ONLY,
    },
    safe(async ({ chain: chainKey, address: target, function: signature, args, blockNumber }) => {
      const cfg = registry.get(chainKey);
      const client = await registry.client(chainKey);
      const fn = parseFunction(signature);
      const result = await client.readContract({
        address: getAddress(target),
        abi: [fn] as Abi,
        functionName: fn.name,
        args: coerceArgs(fn.inputs, args ?? []),
        blockNumber: blockNumber !== undefined ? BigInt(blockNumber) : undefined,
      } as Parameters<PublicClient["readContract"]>[0]);
      return { chain: cfg.key, address: getAddress(target), function: formatAbiItem(fn), result };
    }),
  );

  server.registerTool(
    "get_contract_info",
    {
      title: "Inspect contract",
      description:
        "Explains what is deployed at an address: whether it is a contract, whether it is a proxy, its verified name, compiler and callable functions (via Sourcify). Optionally returns verified source code.",
      inputSchema: {
        chain,
        address,
        includeSource: z.boolean().optional().describe("Include verified source files (truncated)"),
      },
      annotations: READ_ONLY,
    },
    safe(async ({ chain: chainKey, address: target, includeSource }) => {
      const cfg = registry.get(chainKey);
      const client = await registry.client(chainKey);
      const addr = getAddress(target);
      const code = await client.getCode({ address: addr });
      const kind = classifyCode(code);
      if (kind.kind === "empty") {
        return {
          chain: cfg.key,
          address: addr,
          isContract: false,
          summary: "No contract code at this address: it is a regular wallet (EOA) or an unused address.",
          explorer: explorerAddressUrl(cfg, addr),
        };
      }
      if (kind.kind === "delegated") {
        const delegate = await getVerifiedContract(cfg.chainId!, kind.delegate).catch(() => null);
        return {
          chain: cfg.key,
          address: addr,
          isContract: false,
          eip7702Delegation: { delegate: kind.delegate, delegateName: delegate?.name, delegateVerified: Boolean(delegate) },
          summary: `A regular wallet (EOA) that has delegated its code to ${delegate?.name ?? "an unverified contract"} at ${kind.delegate} via EIP-7702, so it can behave like a smart account. The owner's private key still controls it.`,
          warning: delegate
            ? undefined
            : "The EIP-7702 delegate contract is not verified on Sourcify. Unknown delegations are a known way to drain wallets.",
          explorer: explorerAddressUrl(cfg, addr),
        };
      }

      const slot = await client.getStorageAt({ address: addr, slot: EIP1967_IMPLEMENTATION_SLOT }).catch(() => undefined);
      const eip1967Impl = slot && BigInt(slot) !== 0n ? getAddress(`0x${slot.slice(-40)}`) : undefined;

      let verified: VerifiedContract | null = null;
      let verificationError: string | undefined;
      try {
        verified = await getVerifiedContract(cfg.chainId!, addr, { withSources: includeSource });
      } catch (error) {
        verificationError = errorMessage(error);
      }

      const implAddress = eip1967Impl ?? (verified?.implementations[0]?.address as Address | undefined);
      let implementation: VerifiedContract | null = null;
      if (implAddress) {
        implementation = await getVerifiedContract(cfg.chainId!, implAddress).catch(() => null);
      }

      const abiForFunctions = implementation?.abi.length ? implementation.abi : (verified?.abi ?? []);
      const functions = abiForFunctions.filter((i): i is AbiFunction => i.type === "function");

      return {
        chain: cfg.key,
        address: addr,
        isContract: true,
        bytecodeBytes: kind.bytes,
        verified: Boolean(verified),
        verificationError,
        name: verified?.name,
        compiler: verified?.compilerVersion,
        verifiedAt: verified?.verifiedAt,
        proxy: implAddress
          ? {
              implementation: implAddress,
              implementationName: implementation?.name,
              implementationVerified: Boolean(implementation),
              type: verified?.proxyType ?? (eip1967Impl ? "EIP-1967" : undefined),
            }
          : undefined,
        readFunctions: functions
          .filter((f) => f.stateMutability === "view" || f.stateMutability === "pure")
          .map((f) => formatAbiItem(f)),
        writeFunctions: functions
          .filter((f) => f.stateMutability !== "view" && f.stateMutability !== "pure")
          .map((f) => formatAbiItem(f)),
        events: abiForFunctions.filter((i) => i.type === "event").map((e) => formatAbiItem(e)),
        sources: includeSource && verified?.sources ? truncateSources(verified.sources) : undefined,
        warning: verified ? undefined : "Source code is not verified on Sourcify; treat this contract with extra caution.",
        explorer: explorerAddressUrl(cfg, addr),
      };
    }),
  );

  server.registerTool(
    "simulate_transaction",
    {
      title: "Simulate transaction",
      description:
        "Dry-runs a transaction against live chain state without signing or sending anything. Reports whether it would succeed or revert (with reason), the estimated fee, the decoded function call and risk warnings such as unlimited token approvals. Always simulate before asking a user to sign.",
      inputSchema: {
        chain,
        to: address.describe("Recipient or contract address"),
        from: address.optional().describe("Sender address. Many calls revert without the real sender."),
        data: hexData.optional().describe("Calldata (0x...). Omit for a plain native transfer."),
        value: z
          .string()
          .regex(/^\d+(\.\d+)?$/)
          .optional()
          .describe('Native token amount in whole units, e.g. "0.05"'),
      },
      annotations: READ_ONLY,
    },
    safe(async ({ chain: chainKey, to, from, data, value }) => {
      const cfg = registry.get(chainKey);
      const client = await registry.client(chainKey);
      const toAddr = getAddress(to);
      const fromAddr = from ? getAddress(from) : undefined;
      const callData = (data ?? "0x") as Hex;
      const valueWei = value ? parseUnits(value, cfg.nativeDecimals) : 0n;
      const warnings: string[] = [];

      const kind = classifyCode(await client.getCode({ address: toAddr }));
      const toIsContract = kind.kind === "contract";
      const delegate = kind.kind === "delegated" ? kind.delegate : undefined;
      // For EIP-7702 wallets the executed code (and its ABI) lives at the delegate address.
      const codeAddress = delegate ?? toAddr;
      const hasData = callData !== "0x";
      if (kind.kind === "empty" && hasData) {
        warnings.push("Calldata is being sent to an address with no contract code; it will do nothing.");
      }

      let success = false;
      let revertReason: string | undefined;
      let returnData: Hex | undefined;
      try {
        const res = await client.call({ account: fromAddr, to: toAddr, data: callData, value: valueWei });
        success = true;
        returnData = res.data;
      } catch (error) {
        revertReason = errorMessage(error);
      }

      let gasEstimate: bigint | undefined;
      let feeEstimate: string | undefined;
      if (success) {
        try {
          gasEstimate = await client.estimateGas({ account: fromAddr, to: toAddr, data: callData, value: valueWei });
          const gasPrice = await client.getGasPrice();
          feeEstimate = formatAmount(gasEstimate * gasPrice, cfg.nativeDecimals, cfg.nativeSymbol);
        } catch (error) {
          warnings.push(`Gas estimation failed: ${errorMessage(error)}`);
        }
      }

      if (fromAddr && valueWei > 0n) {
        const balance = await client.getBalance({ address: fromAddr });
        if (balance < valueWei) warnings.push(`Sender balance (${formatAmount(balance, cfg.nativeDecimals, cfg.nativeSymbol)}) is lower than the value sent.`);
      }

      let decoded: DecodedCall | undefined;
      let verifiedName: string | undefined;
      if (kind.kind !== "empty") {
        const verified = await getVerifiedContract(cfg.chainId!, codeAddress).catch(() => null);
        verifiedName = verified?.name;
        if (hasData) {
          const abi = await verifiedAbiWithImplementation(cfg, codeAddress).catch(() => undefined);
          decoded = decodeCall(callData, abi);
          if (!verified) warnings.push("Target contract is not verified on Sourcify; its behaviour cannot be checked.");
        }
      }

      const explanation = await explain(client, cfg, {
        to: toAddr,
        toIsContract,
        delegate,
        hasData,
        valueWei,
        decoded,
        verifiedName,
        warnings,
      });

      return {
        chain: cfg.key,
        wouldSucceed: success,
        revertReason,
        explanation,
        decodedCall: decoded,
        gasEstimate,
        feeEstimate,
        returnData: returnData && returnData.length <= 2 + 2 * 1024 ? returnData : undefined,
        warnings,
        note: fromAddr ? undefined : "Simulated without a sender address; results may differ for the real sender.",
      };
    }),
  );
}

async function tokenMeta(client: PublicClient, token: Address): Promise<{ symbol?: string; decimals: number }> {
  const [decimals, symbol] = await Promise.all([
    client.readContract({ address: token, abi: erc20Abi, functionName: "decimals" }),
    client.readContract({ address: token, abi: erc20Abi, functionName: "symbol" }).catch(() => undefined),
  ]);
  return { decimals, symbol };
}

async function verifiedAbiWithImplementation(cfg: ChainConfig, addr: Address): Promise<Abi | undefined> {
  if (cfg.chainId === undefined) return undefined;
  const verified = await getVerifiedContract(cfg.chainId, addr);
  if (!verified) return undefined;
  const impl = verified.implementations[0]?.address;
  if (verified.isProxy && impl) {
    const implVerified = await getVerifiedContract(cfg.chainId, impl).catch(() => null);
    if (implVerified) return [...verified.abi, ...implVerified.abi];
  }
  return verified.abi;
}

async function describeTransfers(
  client: PublicClient,
  logs: { address: Address; args: { from: Address; to: Address; value: bigint } }[],
) {
  const limited = logs.slice(0, 20);
  const metas = new Map<string, Promise<{ symbol?: string; decimals: number } | null>>();
  for (const log of limited) {
    if (!metas.has(log.address)) metas.set(log.address, tokenMeta(client, log.address).catch(() => null));
  }
  return Promise.all(
    limited.map(async (log) => {
      const meta = await metas.get(log.address)!;
      return {
        token: log.address,
        symbol: meta?.symbol,
        from: log.args.from,
        to: log.args.to,
        amount: meta ? formatUnits(log.args.value, meta.decimals) : log.args.value.toString(),
      };
    }),
  );
}

type CodeKind =
  | { kind: "empty" }
  | { kind: "delegated"; delegate: Address }
  | { kind: "contract"; bytes: number };

/** Distinguishes plain wallets, EIP-7702 delegated wallets (code 0xef0100 || address) and contracts. */
export function classifyCode(code: Hex | undefined): CodeKind {
  if (!code || code === "0x") return { kind: "empty" };
  if (code.length === 48 && code.toLowerCase().startsWith("0xef0100")) {
    return { kind: "delegated", delegate: getAddress(`0x${code.slice(8)}`) };
  }
  return { kind: "contract", bytes: (code.length - 2) / 2 };
}

interface ExplainInput {
  to: Address;
  toIsContract: boolean;
  delegate?: Address;
  hasData: boolean;
  valueWei: bigint;
  decoded?: DecodedCall;
  verifiedName?: string;
  warnings: string[];
}

/** Builds a one-paragraph plain-language description of what the transaction does. */
async function explain(client: PublicClient, cfg: ChainConfig, input: ExplainInput): Promise<string> {
  const parts: string[] = [];
  const valueText = input.valueWei > 0n ? formatAmount(input.valueWei, cfg.nativeDecimals, cfg.nativeSymbol) : undefined;

  if (!input.hasData) {
    if (!valueText) return `Sends an empty transaction to ${input.to}; it transfers nothing.`;
    if (input.toIsContract) {
      const name = input.verifiedName ? `the ${input.verifiedName} contract` : "the contract";
      return `Sends ${valueText} to ${name} at ${input.to}, which triggers its receive/fallback logic.`;
    }
    const smart = input.delegate ? ` (an EIP-7702 smart wallet delegated to ${input.verifiedName ?? input.delegate})` : "";
    return `Sends ${valueText} to the wallet ${input.to}${smart}.`;
  }

  if (!input.decoded) {
    parts.push(`Calls a function on ${input.verifiedName ?? "an unidentified contract"} at ${input.to}`);
    if (valueText) parts.push(`and sends ${valueText} with it`);
    return `${parts.join(" ")}. The call could not be decoded, so its effect cannot be explained; only sign if you trust where it came from.`;
  }

  const { functionName, args, source } = input.decoded;
  if (source === "erc20") {
    const meta = await tokenMeta(client, input.to).catch(() => null);
    const amt = (v: unknown) =>
      typeof v === "bigint" && meta ? formatAmount(v, meta.decimals, meta.symbol) : String(v);
    const token = meta?.symbol ?? "tokens";
    if (functionName === "transfer") {
      if (typeof args.recipient === "string" && args.recipient.toLowerCase() === input.to.toLowerCase()) {
        input.warnings.push("Tokens are being sent to the token contract itself; they will most likely be lost.");
      }
      return `Transfers ${amt(args.amount)} to ${args.recipient}.`;
    }
    if (functionName === "approve") {
      const spender = args.spender as Address;
      const spenderCode = await client.getCode({ address: spender }).catch(() => undefined);
      if (!spenderCode || spenderCode === "0x") {
        input.warnings.push("The approved spender is a plain wallet, not a contract. This is a common phishing pattern.");
      }
      if (isUnlimitedApproval(args.amount)) {
        input.warnings.push(`This grants UNLIMITED ${token} spending to ${spender}.`);
        return `Allows ${spender} to spend an unlimited amount of your ${token}.`;
      }
      return `Allows ${spender} to spend up to ${amt(args.amount)} of your ${token}.`;
    }
    if (functionName === "transferFrom") {
      return `Moves ${amt(args.amount)} from ${args.sender} to ${args.recipient} using an existing approval.`;
    }
  }

  parts.push(`Calls ${functionName}() on ${input.verifiedName ?? "the contract"} at ${input.to}`);
  if (valueText) parts.push(`sending ${valueText}`);
  return `${parts.join(", ")}.`;
}

function truncateSources(sources: Record<string, { content: string }>): Record<string, string> {
  const out: Record<string, string> = {};
  let budget = MAX_SOURCE_CHARS;
  for (const [path, { content }] of Object.entries(sources)) {
    if (budget <= 0) {
      out[path] = "[omitted: size limit reached]";
      continue;
    }
    out[path] = content.length > budget ? `${content.slice(0, budget)}\n[truncated]` : content;
    budget -= content.length;
  }
  return out;
}
